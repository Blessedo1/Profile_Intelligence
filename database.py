from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid
import time

Base = declarative_base()

def generate_uuid_v7():
    timestamp_ms = int(time.time() * 1000)
    random_bytes = uuid.uuid4().bytes[6:]
    uuid_int = (timestamp_ms << 80) | int.from_bytes(random_bytes, 'big')
    return uuid.UUID(int=uuid_int)

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid_v7)
    name = Column(String, unique=True, index=True, nullable=False)
    gender = Column(String, nullable=True)
    gender_probability = Column(Float, nullable=True)
    sample_size = Column(Integer, nullable=True)
    age = Column(Integer, nullable=True)
    age_group = Column(String, nullable=True)
    country_id = Column(String, nullable=True)
    country_probability = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

DATABASE_URL = "sqlite:///./profiles.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
