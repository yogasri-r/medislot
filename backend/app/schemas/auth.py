from typing import Optional
from datetime import datetime, date
from pydantic import ConfigDict, BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Plaintext password minimum 6 chars")
    full_name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=10, max_length=15)
    role: str = Field("patient", pattern="^(patient|doctor|hospital_admin|super_admin)$")
    hospital_id: Optional[str] = None
    
    # Optional patient demographic fields if registering as patient
    date_of_birth: Optional[date] = None
    gender: Optional[str] = "other"  # 'male', 'female', 'other'
    blood_group: Optional[str] = None
    preferred_language: Optional[str] = "English"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None

class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str
    role: str
    hospital_id: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut

class RefreshTokenRequest(BaseModel):
    refresh_token: str
