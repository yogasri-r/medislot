from typing import Optional, List, Any
from datetime import datetime
from pydantic import ConfigDict, BaseModel, Field
from app.schemas.auth import UserOut

class DoctorHospitalOut(BaseModel):
    id: str
    doctor_id: str
    hospital_id: str
    hospital_name: Optional[str] = None
    hospital_city: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    consultation_fee: float
    room_number: Optional[str] = None
    is_primary: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class DoctorCreate(BaseModel):
    user_id: str
    license_number: str
    specialty: str
    experience_years: int = 0
    qualification: str
    bio: Optional[str] = None
    languages_spoken: List[str] = ["English"]
    gender: str = "male"
    default_consultation_fee: float = 500.0

class DoctorUpdate(BaseModel):
    specialty: Optional[str] = None
    experience_years: Optional[int] = None
    qualification: Optional[str] = None
    bio: Optional[str] = None
    languages_spoken: Optional[List[str]] = None
    default_consultation_fee: Optional[float] = None
    is_verified: Optional[bool] = None

class DoctorOut(BaseModel):
    id: str
    user_id: str
    license_number: str
    specialty: str
    experience_years: int
    qualification: str
    bio: Optional[str] = None
    languages_spoken: List[str]
    gender: str
    default_consultation_fee: float
    is_verified: bool
    rating_avg: float
    rating_count: int
    user: Optional[UserOut] = None
    hospitals: Optional[List[DoctorHospitalOut]] = []

    model_config = ConfigDict(from_attributes=True)

class DoctorHospitalLink(BaseModel):
    doctor_id: str
    hospital_id: str
    department_id: Optional[str] = None
    consultation_fee: float = 500.0
    room_number: Optional[str] = None
    is_primary: bool = False

class DoctorSearchFilter(BaseModel):
    specialty: Optional[str] = None
    city: Optional[str] = None
    hospital_id: Optional[str] = None
    language: Optional[str] = None
    gender: Optional[str] = None
    verified_only: bool = True
    min_rating: Optional[float] = None
