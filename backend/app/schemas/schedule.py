from typing import Optional, List
from datetime import datetime, date, time
from pydantic import BaseModel, Field, ConfigDict

class SlotOut(BaseModel):
    id: str
    doctor_id: str
    hospital_id: str
    slot_start: datetime
    slot_end: datetime
    slot_start_ist: Optional[str] = None
    slot_end_ist: Optional[str] = None
    status: str  # 'available', 'booked', 'blocked'
    is_suggested: bool = False
    suggestion_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class SlotGenerateRequest(BaseModel):
    doctor_id: str
    hospital_id: str
    start_date: date
    end_date: date

class DateSpecificExceptionCreate(BaseModel):
    doctor_id: str
    hospital_id: Optional[str] = None
    exception_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    exception_type: str = Field("leave", pattern="^(leave|holiday|blocked|custom_hours)$")
    reason: Optional[str] = None

class DateSpecificExceptionOut(BaseModel):
    id: str
    doctor_id: str
    hospital_id: Optional[str] = None
    exception_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    exception_type: str
    reason: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
