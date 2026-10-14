from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class QueueStatusOut(BaseModel):
    appointment_id: str
    appointment_number: str
    doctor_id: str
    doctor_name: str
    hospital_name: str
    status: str
    queue_number: int
    patients_ahead: int
    current_consultation_number: Optional[str] = None
    historical_avg_duration_minutes: float
    live_delay_minutes: int
    estimated_wait_minutes_min: int
    estimated_wait_minutes_max: int
    estimated_wait_formatted: str
    expected_consultation_time_ist: str

    model_config = ConfigDict(from_attributes=True)

class DoctorDailyQueuePatient(BaseModel):
    appointment_id: str
    appointment_number: str
    patient_name: str
    patient_phone: str
    appointment_type: str
    status: str
    slot_time_ist: str
    queue_number: int
    check_in_time: Optional[datetime] = None
    consultation_start_time: Optional[datetime] = None
    estimated_duration_minutes: int
    actual_duration_minutes: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class DoctorDailyQueueOut(BaseModel):
    doctor_id: str
    doctor_name: str
    hospital_id: str
    hospital_name: str
    target_date: str
    total_appointments: int
    completed_count: int
    in_consultation_count: int
    waiting_count: int
    current_delay_minutes: int
    patients: List[DoctorDailyQueuePatient]

    model_config = ConfigDict(from_attributes=True)
