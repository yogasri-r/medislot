from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.auth import UserOut
from app.schemas.doctor import DoctorOut
from app.schemas.hospital import HospitalOut
from app.schemas.patient import PatientOut
from app.schemas.schedule import SlotOut

class AppointmentCreate(BaseModel):
    slot_id: str
    appointment_type: str = Field("new_patient", pattern="^(new_patient|follow_up)$")
    telemedicine_meeting_url: Optional[str] = None
    notes: Optional[str] = None

class AppointmentReschedule(BaseModel):
    new_slot_id: str
    reason: Optional[str] = None

class AppointmentCancel(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)

class AppointmentStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(checked_in|in_consultation|completed|cancelled|no_show)$")
    cancellation_reason: Optional[str] = None

class AppointmentOut(BaseModel):
    id: str
    appointment_number: str
    slot_id: str
    doctor_id: str
    hospital_id: str
    patient_id: str
    appointment_type: str
    status: str
    
    # Timing
    check_in_time: Optional[datetime] = None
    consultation_start_time: Optional[datetime] = None
    consultation_end_time: Optional[datetime] = None
    actual_duration_minutes: Optional[int] = None
    estimated_duration_minutes: int
    estimated_wait_minutes: Optional[int] = None
    queue_number: Optional[int] = None
    
    telemedicine_meeting_url: Optional[str] = None
    cancellation_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    
    # Nested info
    slot: Optional[SlotOut] = None
    doctor: Optional[DoctorOut] = None
    hospital: Optional[HospitalOut] = None
    patient: Optional[PatientOut] = None

    model_config = ConfigDict(from_attributes=True)

class WaitlistJoinRequest(BaseModel):
    doctor_id: str
    hospital_id: str
    preferred_date: date
    preferred_time_range: str = Field("any", pattern="^(morning|afternoon|evening|any)$")

class WaitlistOut(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    hospital_id: str
    preferred_date: date
    preferred_time_range: str
    status: str
    offered_slot_id: Optional[str] = None
    offer_expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WaitlistClaimRequest(BaseModel):
    appointment_type: str = "new_patient"
    telemedicine_meeting_url: Optional[str] = None
