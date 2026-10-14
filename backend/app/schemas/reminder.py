from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class ReminderResponsePayload(BaseModel):
    token: str
    action: str = Field(..., pattern="^(confirmed|cancelled)$")

class ReminderResponseOut(BaseModel):
    status: str
    message: str
    appointment_number: Optional[str] = None
    appointment_status: Optional[str] = None

class DoctorDelayAlertPayload(BaseModel):
    doctor_id: str
    hospital_id: str
    delay_minutes: int = Field(..., gt=0, le=180, description="Delay duration in minutes (1 to 180)")

class NotificationOut(BaseModel):
    id: str
    user_id: str
    appointment_id: Optional[str] = None
    notification_type: str
    channel: str
    recipient: str
    title: str
    body: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
