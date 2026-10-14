from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TriageRequest(BaseModel):
    symptoms: str = Field(..., min_length=2, max_length=1000, description="Patient's symptoms in plain text")
    patient_age: Optional[int] = Field(None, ge=0, le=120)
    patient_gender: Optional[str] = Field(None, description="'male', 'female', 'other'")
    duration_days: Optional[int] = Field(None, ge=0, description="Duration of symptoms in days")

class TriageResponse(BaseModel):
    red_flag_triggered: bool
    urgency_level: str  # 'emergency', 'soon', 'routine'
    primary_specialty: Optional[str] = None
    secondary_specialty: Optional[str] = None
    clinical_reasoning: str
    clarifying_questions: List[str] = []
    emergency_instructions: Optional[str] = None
    emergency_helplines: List[str] = []
    disclaimer: str = (
        "This is an automated AI specialty guidance tool and does not constitute a medical diagnosis. "
        "If you experience severe pain, breathlessness, or worsening symptoms, proceed to the nearest emergency room immediately."
    )
    is_fallback: bool = False

class NLSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="Natural language search query")
    current_city: Optional[str] = None

class NLSearchFilterResult(BaseModel):
    specialty: Optional[str] = None
    city: Optional[str] = None
    hospital_name: Optional[str] = None
    gender: Optional[str] = None
    language: Optional[str] = None
    max_fee: Optional[float] = None
    date_intent: Optional[str] = None  # 'today', 'tomorrow', 'this_weekend', 'next_week', 'any'
    confidence_score: float = 1.0
    summary: str

class NLSearchResponse(BaseModel):
    filters: NLSearchFilterResult
    raw_query: str
    is_fallback: bool = False
    matched_doctors_count: int = 0
    top_doctor_ids: List[str] = []

class ChatMessage(BaseModel):
    role: str  # 'user', 'assistant', 'system'
    content: str

class AIChatRequest(BaseModel):
    messages: List[ChatMessage]
    context_doctor_id: Optional[str] = None

class BookingProposal(BaseModel):
    doctor_id: str
    doctor_name: str
    specialty: str
    hospital_name: str
    hospital_city: str
    slot_id: str
    slot_start_time: str
    consultation_fee: float
    reason: str

class AIChatResponse(BaseModel):
    message: str
    red_flag_triggered: bool = False
    urgency_level: str = "routine"  # 'emergency', 'soon', 'routine'
    suggested_action: Optional[str] = None  # 'consult_specialist', 'emergency', 'book_slot', 'view_appointments'
    specialty_recommendation: Optional[str] = None
    booking_proposal: Optional[BookingProposal] = None
    emergency_protocol: Optional[Dict[str, Any]] = None
    is_fallback: bool = False

class AIQuotaStatus(BaseModel):
    gemini_configured: bool
    model_name: str
    total_calls_today: int
    daily_limit: int
    status: str
