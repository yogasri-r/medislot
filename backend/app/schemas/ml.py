from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class NoShowPredictionRequest(BaseModel):
    appointment_id: Optional[str] = Field(None, description="Existing appointment ID to pull features dynamically")
    lead_time_days: Optional[float] = Field(None, ge=0.0, description="Lead time between booking and appointment in days")
    appointment_type: Optional[str] = Field("new_patient", description="'new_patient' or 'follow_up'")
    day_of_week: Optional[int] = Field(0, ge=0, le=6, description="0=Monday, 6=Sunday")
    hour_of_day: Optional[float] = Field(10.0, ge=0.0, le=24.0, description="Hour of consultation in IST")
    patient_age: Optional[float] = Field(35.0, ge=0.0, le=120.0, description="Patient age in years")
    patient_gender: Optional[str] = Field("Female", description="Patient gender")
    past_appointments: Optional[int] = Field(0, ge=0, description="Number of prior completed/booked appointments")
    past_no_shows: Optional[int] = Field(0, ge=0, description="Number of prior unfulfilled appointments")
    doctor_specialty: Optional[str] = Field("General Medicine", description="Doctor clinical specialty")
    doctor_experience_years: Optional[int] = Field(10, ge=0, description="Doctor experience in years")
    consultation_fee: Optional[float] = Field(500.0, ge=0.0, description="Consultation fee in INR")

class NoShowPredictionResponse(BaseModel):
    no_show_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: str = Field(..., description="'low' (<0.25), 'medium' (0.25-0.45), 'high' (>=0.45)")
    is_high_risk: bool
    recommended_action: str
    top_risk_factors: List[str]
    model_version: str

    model_config = ConfigDict(from_attributes=True)

class DurationPredictionRequest(BaseModel):
    appointment_type: str = Field("new_patient", description="'new_patient' or 'follow_up'")
    doctor_specialty: str = Field("Cardiology", description="Doctor specialty")
    day_of_week: int = Field(1, ge=0, le=6, description="0=Monday, 6=Sunday")
    hour_of_day: float = Field(10.5, ge=0.0, le=24.0, description="Hour of consultation in IST")
    patient_age: float = Field(42.0, ge=0.0, le=120.0, description="Patient age")
    doctor_experience_years: int = Field(12, ge=0, description="Doctor experience in years")
    estimated_duration_minutes: Optional[int] = Field(20, description="Static template duration")

class DurationPredictionResponse(BaseModel):
    predicted_duration_minutes: float
    template_duration_minutes: int
    variance_minutes: float
    clinical_load: str
    model_version: str

    model_config = ConfigDict(from_attributes=True)

class MLModelInfoResponse(BaseModel):
    no_show_model: Dict[str, Any]
    wait_time_model: Dict[str, Any]
    status: str
