from typing import Optional, List
from datetime import datetime
from pydantic import ConfigDict, BaseModel, Field

class HospitalCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    slug: str = Field(..., min_length=3, max_length=200)
    address: str
    city: str = Field(..., max_length=100)
    state: str = Field("Tamil Nadu", max_length=100)
    postal_code: str = Field(..., max_length=20)
    phone: str = Field(..., max_length=20)
    email: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class HospitalUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: Optional[bool] = None

class HospitalOut(BaseModel):
    id: str
    name: str
    slug: str
    address: str
    city: str
    state: str
    postal_code: str
    phone: str
    email: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DepartmentCreate(BaseModel):
    hospital_id: str
    name: str = Field(..., max_length=100)
    description: Optional[str] = None

class DepartmentOut(BaseModel):
    id: str
    hospital_id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
