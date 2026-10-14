from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.models.doctor import Doctor
from app.models.schedule import Slot, DateSpecificException
from app.schemas.schedule import SlotOut, SlotGenerateRequest, DateSpecificExceptionCreate, DateSpecificExceptionOut
from app.services.availability import get_slots_for_doctor, generate_slots_for_doctor, convert_utc_to_ist_str

router = APIRouter(prefix="/slots", tags=["Slots & Availability"])

@router.get("", response_model=List[SlotOut])
def list_slots(
    doctor_id: str,
    target_date: date = Query(default_factory=date.today),
    hospital_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lists bookable slots for a doctor on a specific date.
    Returns both UTC ISO timestamps and formatted IST display times.
    """
    slots = get_slots_for_doctor(doctor_id, hospital_id, target_date, db)
    results = []
    for s in slots:
        results.append(SlotOut(
            id=s.id,
            doctor_id=s.doctor_id,
            hospital_id=s.hospital_id,
            slot_start=s.slot_start,
            slot_end=s.slot_end,
            slot_start_ist=convert_utc_to_ist_str(s.slot_start),
            slot_end_ist=convert_utc_to_ist_str(s.slot_end),
            status=s.status,
            is_suggested=False
        ))
    return results

@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_slots(
    payload: SlotGenerateRequest,
    current_user: User = Depends(require_roles(["doctor", "hospital_admin", "super_admin"])),
    db: Session = Depends(get_db)
):
    """Generates clinical appointment slots for a doctor over a date range."""
    created = generate_slots_for_doctor(
        doctor_id=payload.doctor_id,
        hospital_id=payload.hospital_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        db=db
    )
    return {"message": f"Successfully generated {created} new slots.", "slots_created": created}

@router.post("/exceptions", response_model=DateSpecificExceptionOut, status_code=status.HTTP_201_CREATED)
def add_exception(
    payload: DateSpecificExceptionCreate,
    current_user: User = Depends(require_roles(["doctor", "hospital_admin", "super_admin"])),
    db: Session = Depends(get_db)
):
    """Adds a doctor leave or blocked shift exception."""
    exc = DateSpecificException(
        doctor_id=payload.doctor_id,
        hospital_id=payload.hospital_id,
        exception_date=payload.exception_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        exception_type=payload.exception_type,
        reason=payload.reason,
        is_active=True
    )
    db.add(exc)
    db.commit()
    db.refresh(exc)
    return exc
