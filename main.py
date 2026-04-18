from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import httpx
from datetime import datetime
from typing import List, Optional
from .database import get_db, Profile, generate_uuid_v7
from .schemas import ProfileResponse, ProfileListResponse

app = FastAPI(title="Profile Intelligence Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_age_group(age: Optional[int]) -> Optional[str]:
    if age is None:
        return None
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"

@app.post("/api/profiles", status_code=201)
async def create_profile(payload: dict, db: Session = Depends(get_db)):
    name = payload.get("name")
    if not name or not isinstance(name, str) or len(name.strip()) == 0:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Missing or empty name"})

    name = name.strip().lower()

    # Idempotency: check if profile already exists
    existing = db.query(Profile).filter(Profile.name == name).first()
    if existing:
        return {
            "status": "success",
            "message": "Profile already exists",
            "data": existing
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Call all 3 APIs in parallel
            genderize_task = client.get("https://api.genderize.io/", params={"name": name})
            agify_task = client.get("https://api.agify.io/", params={"name": name})
            nationalize_task = client.get("https://api.nationalize.io/", params={"name": name})

            genderize, agify, nationalize = await asyncio.gather(
                genderize_task, agify_task, nationalize_task, return_exceptions=True
            )

        # Validate responses
        if isinstance(genderize, Exception) or genderize.status_code != 200 or not genderize.json().get("gender"):
            raise HTTPException(status_code=502, detail={"status": "error", "message": "Genderize returned an invalid response"})

        if isinstance(agify, Exception) or agify.status_code != 200 or agify.json().get("age") is None:
            raise HTTPException(status_code=502, detail={"status": "error", "message": "Agify returned an invalid response"})

        if isinstance(nationalize, Exception) or nationalize.status_code != 200 or not nationalize.json().get("country"):
            raise HTTPException(status_code=502, detail={"status": "error", "message": "Nationalize returned an invalid response"})

        g_data = genderize.json()
        a_data = agify.json()
        n_data = nationalize.json()

        # Get country with highest probability
        countries = n_data.get("country", [])
        best_country = max(countries, key=lambda x: x.get("probability", 0)) if countries else None

        profile = Profile(
            name=name,
            gender=g_data.get("gender"),
            gender_probability=round(g_data.get("probability", 0), 4),
            sample_size=g_data.get("count", 0),
            age=a_data.get("age"),
            age_group=get_age_group(a_data.get("age")),
            country_id=best_country.get("country_id") if best_country else None,
            country_probability=round(best_country.get("probability", 0), 4) if best_country else None,
        )

        db.add(profile)
        db.commit()
        db.refresh(profile)

        return {
            "status": "success",
            "data": profile
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "error", "message": "Internal server error"})


@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail={"status": "error", "message": "Profile not found"})
    return {"status": "success", "data": profile}


@app.get("/api/profiles")
def list_profiles(
    gender: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Profile)

    if gender:
        query = query.filter(Profile.gender == gender.lower())
    if country_id:
        query = query.filter(Profile.country_id == country_id.upper())
    if age_group:
        query = query.filter(Profile.age_group == age_group.lower())

    profiles = query.all()
    return {
        "status": "success",
        "count": len(profiles),
        "data": profiles
    }


@app.delete("/api/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail={"status": "error", "message": "Profile not found"})
    db.delete(profile)
    db.commit()
    return None
