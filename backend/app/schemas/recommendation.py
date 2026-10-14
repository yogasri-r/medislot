from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.doctor import DoctorOut

class DoctorRecommendationScore(BaseModel):
    doctor_id: str
    composite_score: float = Field(..., ge=0.0, le=1.0)
    score_breakdown: Dict[str, float]
    explanation: str
    earliest_available_slot_utc: Optional[str] = None
    earliest_available_slot_ist: Optional[str] = None
    doctor: DoctorOut

    model_config = ConfigDict(from_attributes=True)

class SmartSlotOut(BaseModel):
    id: str
    doctor_id: str
    hospital_id: str
    slot_start: str
    slot_end: str
    slot_start_ist: str
    slot_end_ist: str
    status: str
    score: float
    is_suggested: bool = False
    suggestion_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class SmartSlotsResponse(BaseModel):
    doctor_id: str
    target_date: str
    total_slots: int
    available_slots: int
    suggested_slots: List[SmartSlotOut]
    all_slots: List[SmartSlotOut]

    model_config = ConfigDict(from_attributes=True)
