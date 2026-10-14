from datetime import datetime, timezone, timedelta, date
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.appointment import Waitlist, Appointment, Notification
from app.models.schedule import Slot
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.hospital import Hospital
from app.core.dependencies import log_audit

def add_to_waitlist(
    patient_id: str,
    doctor_id: str,
    hospital_id: str,
    preferred_date: date,
    preferred_time_range: str,
    db: Session
) -> Waitlist:
    """Adds a patient to the waitlist for a specific doctor, hospital, and date."""
    existing = db.query(Waitlist).filter(
        Waitlist.patient_id == patient_id,
        Waitlist.doctor_id == doctor_id,
        Waitlist.preferred_date == preferred_date,
        Waitlist.status == "waiting"
    ).first()

    if existing:
        return existing

    wait_entry = Waitlist(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        preferred_date=preferred_date,
        preferred_time_range=preferred_time_range,
        status="waiting"
    )
    db.add(wait_entry)
    db.commit()
    db.refresh(wait_entry)
    return wait_entry

def process_freed_slot_waitlist(freed_slot: Slot, db: Session) -> Optional[Waitlist]:
    """
    Triggered when an appointment is cancelled or rescheduled.
    Finds the earliest waitlisted patient for this doctor and date, and issues a 30-min offer.
    """
    import zoneinfo
    from app.core.config import settings
    ist_zone = zoneinfo.ZoneInfo(settings.DEFAULT_TIMEZONE)
    slot_local_date = freed_slot.slot_start.astimezone(ist_zone).date()

    # Find earliest waiting patient
    wait_entry = db.query(Waitlist).filter(
        Waitlist.doctor_id == freed_slot.doctor_id,
        Waitlist.preferred_date == slot_local_date,
        Waitlist.status == "waiting"
    ).order_by(Waitlist.created_at.asc()).first()

    if not wait_entry:
        return None

    # Offer slot with 30-minute claim window
    offer_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
    wait_entry.status = "offered"
    wait_entry.offered_slot_id = freed_slot.id
    wait_entry.offer_expires_at = offer_expiry

    # Create notification record
    patient = db.query(Patient).filter(Patient.id == wait_entry.patient_id).first()
    if patient and patient.user:
        notif = Notification(
            user_id=patient.user_id,
            notification_type="waitlist_offer",
            channel="email",
            recipient=patient.user.email,
            title="A Doctor Slot Just Opened Up on MediSlot!",
            body=f"A slot with Dr. {freed_slot.doctor.user.full_name if freed_slot.doctor else 'Doctor'} has become available. You have 30 minutes to claim it.",
            status="pending"
        )
        db.add(notif)

    db.commit()
    db.refresh(wait_entry)
    return wait_entry
