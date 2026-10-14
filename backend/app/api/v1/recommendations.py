from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_current_user
from app.models.user import User
from app.models.patient import Patient
from app.schemas.recommendation import DoctorRecommendationScore, SmartSlotsResponse
from app.services.recommendation import recommend_doctors
from app.services.smart_slots import rank_slots_for_doctor

router = APIRouter(prefix="/recommendations", tags=["Recommendations & Smart Slots"])

@router.get("/doctors", response_model=List[DoctorRecommendationScore])
def get_recommended_doctors(
    specialty: Optional[str] = Query(None, description="Medical specialty to match"),
    city: Optional[str] = Query(None, description="Preferred patient city for proximity scoring"),
    hospital_id: Optional[str] = Query(None, description="Optional hospital filter"),
    language: Optional[str] = Query(None, description="Preferred language (e.g., Tamil, English)"),
    gender: Optional[str] = Query(None, description="Doctor gender preference"),
    max_fee: Optional[float] = Query(None, description="Maximum consultation fee filter"),
    verified_only: bool = Query(True, description="Only verified doctors"),
    limit: int = Query(10, ge=1, le=50, description="Max number of recommendations"),
    db: Session = Depends(get_db)
):
    """
    Multi-factor doctor recommendation ranking:
    Calculates weighted composite score based on:
    - Specialty match (0.30)
    - Earliest available slot (0.25)
    - Bayesian rating shrinkage (0.20)
    - Geographic proximity across Western Tamil Nadu healthcare clusters (0.15)
    - Years of clinical experience (0.10)
    - Matching language bonus (+0.05)
    """
    return recommend_doctors(
        specialty=specialty,
        city=city,
        hospital_id=hospital_id,
        language=language,
        gender=gender,
        max_fee=max_fee,
        verified_only=verified_only,
        limit=limit,
        db=db
    )

@router.get("/smart-slots", response_model=SmartSlotsResponse)
def get_smart_slots(
    doctor_id: str = Query(..., description="Doctor ID"),
    target_date: date = Query(..., description="Target appointment date (YYYY-MM-DD)"),
    patient_id: Optional[str] = Query(None, description="Optional patient ID for preference learning"),
    hospital_id: Optional[str] = Query(None, description="Optional hospital ID"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Ranks outpatient consultation slots and identifies Top 3 'Suggested' slots.
    Considers:
    - Patient's historical consultation time preference
    - Schedule gap-filling (efficient doctor block packing)
    - Late-day accumulated delay risk mitigation
    - Prime morning energy slots
    """
    # If patient_id not explicitly given, try extracting from authenticated user
    resolved_patient_id = patient_id
    if not resolved_patient_id and current_user and current_user.role == "patient":
        pat = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if pat:
            resolved_patient_id = pat.id

    return rank_slots_for_doctor(
        doctor_id=doctor_id,
        target_date=target_date,
        patient_id=resolved_patient_id,
        hospital_id=hospital_id,
        db=db
    )
