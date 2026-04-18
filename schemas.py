from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class ProfileResponse(BaseModel):
    id: str
    name: str
    gender: Optional[str]
    gender_probability: Optional[float]
    sample_size: Optional[int]
    age: Optional[int]
    age_group: Optional[str]
    country_id: Optional[str]
    country_probability: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True

class ProfileListResponse(BaseModel):
    status: str = "success"
    count: int
    data: List[ProfileResponse]
