import uuid
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from fastapi import HTTPException, status
from app.models.appointment import Appointment, Waitlist
from app.models.schedule import Slot
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.user import User
from app.core.dependencies import log_audit
from app.services.waitlist import process_freed_slot_waitlist
from app.services.reminder import schedule_appointment_reminders, send_reschedule_alert, send_cancellation_alert

_booking_lock = threading.Lock()

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def generate_appointment_number() -> str:
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uid = uuid.uuid4().hex[:6].upper()
    return f"MED-{today_str}-{short_uid}"

def book_appointment_tx(
    patient_id: str,
    slot_id: str,
    appointment_type: str,
    notes: Optional[str],
    telemedicine_url: Optional[str],
    current_user_id: str,
    db: Session
) -> Appointment:
    """
    Books an appointment in a concurrency-safe manner.
    Combines row-locking (for PostgreSQL) and an in-process mutex (for SQLite/local concurrency)
    to eliminate race conditions and guarantee zero double bookings.
    """
    with _booking_lock:
        try:
            # Row-level lock
            slot = db.query(Slot).filter(Slot.id == slot_id).with_for_update().first()
            if not slot:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found.")
            
            if slot.status != "available":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This slot is no longer available; it was booked by another patient."
                )

            # Active appointment verification
            active_existing = db.query(Appointment).filter(
                Appointment.slot_id == slot_id,
                Appointment.status.in_(["booked", "checked_in", "in_consultation"])
            ).first()
            if active_existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This slot already has an active booking."
                )

            # Immediately update slot status
            slot.status = "booked"

            # Estimated consultation duration (new patient: 25 mins, follow up: 15 mins)
            est_duration = 25 if appointment_type == "new_patient" else 15

            appointment = Appointment(
                appointment_number=generate_appointment_number(),
                slot_id=slot.id,
                doctor_id=slot.doctor_id,
                hospital_id=slot.hospital_id,
                patient_id=patient_id,
                appointment_type=appointment_type,
                status="booked",
                estimated_duration_minutes=est_duration,
                telemedicine_meeting_url=telemedicine_url,
                notes=notes
            )
            db.add(appointment)
            db.commit()
            db.refresh(appointment)

        except (IntegrityError, OperationalError):
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict: This slot was booked concurrently by another patient."
            )

    log_audit(
        db=db,
        user_id=current_user_id,
        action="CREATE_APPOINTMENT",
        resource_type="appointment",
        resource_id=appointment.id,
        hospital_id=slot.hospital_id,
        details={"appointment_number": appointment.appointment_number, "slot_id": slot_id}
    )

    # Schedule reminders and dispatch confirmation
    schedule_appointment_reminders(appointment, db)

    return appointment

def reschedule_appointment(
    appointment_id: str,
    new_slot_id: str,
    current_user: User,
    db: Session
) -> Appointment:
    """
    Reschedules an existing appointment to a new slot.
    Frees the old slot and checks if waitlisted patients can claim it.
    """
    with _booking_lock:
        try:
            appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
            if not appt:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

            if appt.status not in ["booked", "checked_in"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot reschedule an appointment in '{appt.status}' state."
                )

            # Lock new slot
            new_slot = db.query(Slot).filter(Slot.id == new_slot_id).with_for_update().first()
            if not new_slot or new_slot.status != "available":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The requested new slot is not available."
                )

            # Old slot
            old_slot = db.query(Slot).filter(Slot.id == appt.slot_id).first()
            if old_slot:
                old_slot.status = "available"

            # Assign new slot
            new_slot.status = "booked"
            appt.slot_id = new_slot.id
            appt.doctor_id = new_slot.doctor_id
            appt.hospital_id = new_slot.hospital_id

            db.commit()
            db.refresh(appt)

        except (IntegrityError, OperationalError):
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="New slot was booked concurrently.")

    # Trigger waitlist on the freed old slot
    if old_slot:
        process_freed_slot_waitlist(old_slot, db)

    log_audit(
        db=db,
        user_id=current_user.id,
        action="RESCHEDULE_APPOINTMENT",
        resource_type="appointment",
        resource_id=appt.id,
        hospital_id=appt.hospital_id,
        details={"old_slot_id": old_slot.id if old_slot else None, "new_slot_id": new_slot_id}
    )

    # Dispatch reschedule notification and adjust reminder schedule
    if old_slot and new_slot:
        send_reschedule_alert(appt, old_slot, new_slot, db)

    return appt

def cancel_appointment(
    appointment_id: str,
    reason: str,
    current_user: User,
    db: Session
) -> Appointment:
    """
    Cancels an appointment, transitions state to 'cancelled', frees slot,
    and automatically triggers waitlist notification for waiting patients.
    """
    with _booking_lock:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

        # State Machine Check
        if appt.status in ["completed", "cancelled", "no_show"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel appointment with status '{appt.status}'."
            )

        appt.status = "cancelled"
        appt.cancellation_reason = reason
        appt.cancelled_by_user_id = current_user.id

        # Free the slot
        slot = db.query(Slot).filter(Slot.id == appt.slot_id).first()
        if slot:
            slot.status = "available"

        db.commit()
        db.refresh(appt)

    # Trigger waitlist engine on freed slot
    if slot:
        process_freed_slot_waitlist(slot, db)

    log_audit(
        db=db,
        user_id=current_user.id,
        action="CANCEL_APPOINTMENT",
        resource_type="appointment",
        resource_id=appt.id,
        hospital_id=appt.hospital_id,
        details={"reason": reason}
    )

    # Dispatch cancellation notification and cancel pending reminders
    send_cancellation_alert(appt, reason, db)

    return appt

def update_appointment_lifecycle_status(
    appointment_id: str,
    new_status: str,
    cancellation_reason: Optional[str],
    current_user: User,
    db: Session
) -> Appointment:
    """
    Manages appointment lifecycle state transitions:
    - booked -> checked_in -> in_consultation -> completed
    - booked/checked_in -> cancelled, no_show
    Rejects invalid state transitions.
    """
    with _booking_lock:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

        current_status = appt.status

        valid_transitions = {
            "booked": ["checked_in", "cancelled", "no_show"],
            "checked_in": ["in_consultation", "cancelled", "no_show"],
            "in_consultation": ["completed"],
            "completed": [],
            "cancelled": [],
            "no_show": []
        }

        allowed = valid_transitions.get(current_status, [])
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition from '{current_status}' to '{new_status}'."
            )

        appt.status = new_status
        now = utc_now()

        slot = None
        if new_status == "checked_in":
            appt.check_in_time = now
        elif new_status == "in_consultation":
            appt.consultation_start_time = now
        elif new_status == "completed":
            appt.consultation_end_time = now
            if appt.consultation_start_time:
                start_t = appt.consultation_start_time
                if start_t.tzinfo is None:
                    start_t = start_t.replace(tzinfo=timezone.utc)
                diff = (now - start_t).total_seconds() / 60.0
                appt.actual_duration_minutes = max(1, int(round(diff)))
            else:
                appt.actual_duration_minutes = appt.estimated_duration_minutes
        elif new_status == "cancelled":
            appt.cancellation_reason = cancellation_reason or "Cancelled by clinical staff"
            slot = db.query(Slot).filter(Slot.id == appt.slot_id).first()
            if slot:
                slot.status = "available"

        db.commit()
        db.refresh(appt)

    if slot:
        process_freed_slot_waitlist(slot, db)

    log_audit(
        db=db,
        user_id=current_user.id,
        action="UPDATE_STATUS",
        resource_type="appointment",
        resource_id=appt.id,
        hospital_id=appt.hospital_id,
        details={"from_status": current_status, "to_status": new_status}
    )

    return appt
