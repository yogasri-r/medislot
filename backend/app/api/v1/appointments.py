from typing import List, Optional
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.schedule import Slot
from app.models.appointment import Appointment
from app.schemas.appointment import (
    AppointmentCreate, AppointmentReschedule, AppointmentCancel, AppointmentStatusUpdate, AppointmentOut
)
from app.schemas.schedule import SlotOut
from app.schemas.doctor import DoctorOut
from app.schemas.hospital import HospitalOut
from app.schemas.patient import PatientOut
from app.services.booking import book_appointment_tx, reschedule_appointment, cancel_appointment, update_appointment_lifecycle_status
from app.services.availability import convert_utc_to_ist_str

router = APIRouter(prefix="/appointments", tags=["Appointments"])

def _serialize_appointment(appt: Appointment) -> AppointmentOut:
    slot_out = None
    if appt.slot:
        slot_out = SlotOut(
            id=appt.slot.id,
            doctor_id=appt.slot.doctor_id,
            hospital_id=appt.slot.hospital_id,
            slot_start=appt.slot.slot_start,
            slot_end=appt.slot.slot_end,
            slot_start_ist=convert_utc_to_ist_str(appt.slot.slot_start),
            slot_end_ist=convert_utc_to_ist_str(appt.slot.slot_end),
            status=appt.slot.status
        )

    return AppointmentOut(
        id=appt.id,
        appointment_number=appt.appointment_number,
        slot_id=appt.slot_id,
        doctor_id=appt.doctor_id,
        hospital_id=appt.hospital_id,
        patient_id=appt.patient_id,
        appointment_type=appt.appointment_type,
        status=appt.status,
        check_in_time=appt.check_in_time,
        consultation_start_time=appt.consultation_start_time,
        consultation_end_time=appt.consultation_end_time,
        actual_duration_minutes=appt.actual_duration_minutes,
        estimated_duration_minutes=appt.estimated_duration_minutes,
        estimated_wait_minutes=appt.estimated_wait_minutes,
        queue_number=appt.queue_number,
        telemedicine_meeting_url=appt.telemedicine_meeting_url,
        cancellation_reason=appt.cancellation_reason,
        notes=appt.notes,
        created_at=appt.created_at,
        slot=slot_out
    )

@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def book_appointment(
    payload: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Books a slot with transactional concurrency control.
    Prevents double booking with row locking and unique constraints.
    """
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only registered patients can book appointments. Please create a patient profile."
        )

    appt = book_appointment_tx(
        patient_id=patient.id,
        slot_id=payload.slot_id,
        appointment_type=payload.appointment_type,
        notes=payload.notes,
        telemedicine_url=payload.telemedicine_meeting_url,
        current_user_id=current_user.id,
        db=db
    )
    return _serialize_appointment(appt)

@router.get("", response_model=List[AppointmentOut])
def list_appointments(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists appointments scoped to the authenticated role."""
    query = db.query(Appointment).options(
        joinedload(Appointment.slot),
        joinedload(Appointment.doctor),
        joinedload(Appointment.hospital)
    )

    if current_user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            return []
        query = query.filter(Appointment.patient_id == patient.id)
    elif current_user.role == "doctor":
        doc = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doc:
            return []
        query = query.filter(Appointment.doctor_id == doc.id)
    elif current_user.role == "hospital_admin":
        query = query.filter(Appointment.hospital_id == current_user.hospital_id)

    if status_filter:
        query = query.filter(Appointment.status == status_filter)

    appts = query.order_by(Appointment.created_at.desc()).all()
    return [_serialize_appointment(a) for a in appts]

@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches single appointment record with access check."""
    appt = db.query(Appointment).options(
        joinedload(Appointment.slot),
        joinedload(Appointment.doctor),
        joinedload(Appointment.hospital)
    ).filter(Appointment.id == appointment_id).first()

    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    # Scoped access check
    if current_user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or appt.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif current_user.role == "hospital_admin":
        if str(appt.hospital_id) != str(current_user.hospital_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to other hospital data")

    return _serialize_appointment(appt)

@router.post("/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule(
    appointment_id: str,
    payload: AppointmentReschedule,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reschedules appointment to a new slot."""
    appt = reschedule_appointment(
        appointment_id=appointment_id,
        new_slot_id=payload.new_slot_id,
        current_user=current_user,
        db=db
    )
    return _serialize_appointment(appt)

@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel(
    appointment_id: str,
    payload: AppointmentCancel,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancels appointment and triggers waitlist auto-offers for freed slot."""
    appt = cancel_appointment(
        appointment_id=appointment_id,
        reason=payload.reason,
        current_user=current_user,
        db=db
    )
    return _serialize_appointment(appt)

@router.post("/{appointment_id}/status", response_model=AppointmentOut)
def update_status(
    appointment_id: str,
    payload: AppointmentStatusUpdate,
    current_user: User = Depends(require_roles(["doctor", "hospital_admin", "super_admin"])),
    db: Session = Depends(get_db)
):
    """
    Doctor/Staff updates appointment clinical lifecycle status:
    checked_in -> in_consultation -> completed
    """
    appt = update_appointment_lifecycle_status(
        appointment_id=appointment_id,
        new_status=payload.status,
        cancellation_reason=payload.cancellation_reason,
        current_user=current_user,
        db=db
    )
    return _serialize_appointment(appt)
