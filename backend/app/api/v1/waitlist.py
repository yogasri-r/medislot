from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.patient import Patient
from app.models.appointment import Waitlist
from app.schemas.appointment import WaitlistJoinRequest, WaitlistOut, WaitlistClaimRequest, AppointmentOut
from app.services.waitlist import add_to_waitlist
from app.services.booking import book_appointment_tx
from app.api.v1.appointments import _serialize_appointment

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])

@router.post("", response_model=WaitlistOut, status_code=status.HTTP_201_CREATED)
def join_waitlist_endpoint(
    payload: WaitlistJoinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient registers for waitlist on a fully booked date."""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only registered patients can join the waitlist.")

    entry = add_to_waitlist(
        patient_id=patient.id,
        doctor_id=payload.doctor_id,
        hospital_id=payload.hospital_id,
        preferred_date=payload.preferred_date,
        preferred_time_range=payload.preferred_time_range,
        db=db
    )
    return entry

@router.get("/my", response_model=List[WaitlistOut])
def get_my_waitlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists active waitlist entries for current patient."""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        return []
    return db.query(Waitlist).filter(Waitlist.patient_id == patient.id).order_by(Waitlist.created_at.desc()).all()

@router.post("/{waitlist_id}/claim", response_model=AppointmentOut)
def claim_waitlist_offer(
    waitlist_id: str,
    payload: WaitlistClaimRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient claims a time-limited offered slot from cancellation."""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient profile required.")

    wait_entry = db.query(Waitlist).filter(
        Waitlist.id == waitlist_id,
        Waitlist.patient_id == patient.id
    ).first()

    if not wait_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waitlist record not found.")

    if wait_entry.status != "offered" or not wait_entry.offered_slot_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active offer available on this waitlist entry.")

    # Check expiration
    now = datetime.now(timezone.utc)
    if wait_entry.offer_expires_at:
        # ensure timezone aware comparison
        exp = wait_entry.offer_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            wait_entry.status = "expired"
            db.commit()
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="This waitlist offer has expired.")

    # Claim & book
    appt = book_appointment_tx(
        patient_id=patient.id,
        slot_id=wait_entry.offered_slot_id,
        appointment_type=payload.appointment_type,
        notes="Booked via auto-waitlist claim",
        telemedicine_url=payload.telemedicine_meeting_url,
        current_user_id=current_user.id,
        db=db
    )

    wait_entry.status = "accepted"
    db.commit()

    return _serialize_appointment(appt)
