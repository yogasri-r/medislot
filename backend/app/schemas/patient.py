from typing import Optional
from datetime import datetime, date
from pydantic import ConfigDict, BaseModel, Field
from app.schemas.auth import UserOut

class PatientCreate(BaseModel):
    user_id: str
    date_of_birth: date
    gender: str
    blood_group: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    preferred_language: str = "English"

class PatientUpdate(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    preferred_language: Optional[str] = None

class PatientOut(BaseModel):
    id: str
    user_id: str
    date_of_birth: date
    gender: str
    blood_group: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    preferred_language: str
    created_at: datetime
    user: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)
