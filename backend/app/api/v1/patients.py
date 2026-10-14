from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.patient import Patient
from app.schemas.patient import PatientUpdate, PatientOut

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.get("/me", response_model=PatientOut)
def get_my_patient_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns the patient profile for the current logged-in user."""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found for this user.")
    return PatientOut(
        id=patient.id,
        user_id=patient.user_id,
        date_of_birth=patient.date_of_birth,
        gender=patient.gender,
        blood_group=patient.blood_group,
        emergency_contact_name=patient.emergency_contact_name,
        emergency_contact_phone=patient.emergency_contact_phone,
        preferred_language=patient.preferred_language,
        created_at=patient.created_at,
        user=current_user
    )

@router.put("/me", response_model=PatientOut)
def update_my_patient_profile(
    payload: PatientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates current patient demographics and preferences."""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found.")
    
    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(patient, k, v)
    
    db.commit()
    db.refresh(patient)
    return get_my_patient_profile(current_user, db)
