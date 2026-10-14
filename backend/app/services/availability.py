from datetime import datetime, date, time, timezone, timedelta
from typing import List, Optional, Tuple
import zoneinfo
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.schedule import WeeklyAvailabilityTemplate, DateSpecificException, Slot
from app.models.doctor import Doctor, DoctorHospital
from app.core.config import settings

IST_ZONE = zoneinfo.ZoneInfo(settings.DEFAULT_TIMEZONE)

def convert_utc_to_ist_str(utc_dt: datetime) -> str:
    """Converts a UTC datetime to formatted IST string (e.g. '10:30 AM')."""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    ist_dt = utc_dt.astimezone(IST_ZONE)
    return ist_dt.strftime("%I:%M %p")

def generate_slots_for_doctor(
    doctor_id: str,
    hospital_id: str,
    start_date: date,
    end_date: date,
    db: Session
) -> int:
    """
    Generates bookable slots for a doctor at a given hospital across a date range.
    Uses WeeklyAvailabilityTemplates and honors DateSpecificExceptions (leaves/blocked times).
    Guarantees no duplicate slots using UNIQUE (doctor_id, slot_start).
    """
    # 1. Fetch weekly templates for this doctor and hospital
    templates = db.query(WeeklyAvailabilityTemplate).filter(
        WeeklyAvailabilityTemplate.doctor_id == doctor_id,
        WeeklyAvailabilityTemplate.hospital_id == hospital_id,
        WeeklyAvailabilityTemplate.is_active == True
    ).all()

    if not templates:
        return 0

    # 2. Fetch exceptions in this date range
    exceptions = db.query(DateSpecificException).filter(
        DateSpecificException.doctor_id == doctor_id,
        DateSpecificException.exception_date >= start_date,
        DateSpecificException.exception_date <= end_date,
        DateSpecificException.is_active == True
    ).all()

    exceptions_by_date = {}
    for exc in exceptions:
        exceptions_by_date.setdefault(exc.exception_date, []).append(exc)

    slots_created = 0
    curr_date = start_date

    while curr_date <= end_date:
        weekday = curr_date.weekday()  # 0 = Monday, 6 = Sunday
        day_templates = [t for t in templates if t.day_of_week == weekday]
        day_exceptions = exceptions_by_date.get(curr_date, [])

        # Check full day leave
        is_full_day_off = any(
            exc.exception_type in ["leave", "holiday", "blocked"] and exc.start_time is None
            for exc in day_exceptions
        )

        if not is_full_day_off and day_templates:
            for tmpl in day_templates:
                slot_minutes = tmpl.slot_duration_minutes or 20
                
                # Combine date + template time in IST, then convert to UTC
                start_dt_ist = datetime.combine(curr_date, tmpl.start_time, tzinfo=IST_ZONE)
                end_dt_ist = datetime.combine(curr_date, tmpl.end_time, tzinfo=IST_ZONE)

                start_dt_utc = start_dt_ist.astimezone(timezone.utc)
                end_dt_utc = end_dt_ist.astimezone(timezone.utc)

                slot_cursor = start_dt_utc
                while slot_cursor + timedelta(minutes=slot_minutes) <= end_dt_utc:
                    slot_end = slot_cursor + timedelta(minutes=slot_minutes)

                    # Check partial day exceptions
                    slot_start_time = slot_cursor.astimezone(IST_ZONE).time()
                    slot_end_time = slot_end.astimezone(IST_ZONE).time()

                    is_blocked = False
                    for exc in day_exceptions:
                        if exc.start_time and exc.end_time:
                            if not (slot_end_time <= exc.start_time or slot_start_time >= exc.end_time):
                                is_blocked = True
                                break

                    # Check if slot already exists in DB (enforce unique doctor_id, slot_start)
                    existing = db.query(Slot).filter(
                        Slot.doctor_id == doctor_id,
                        Slot.slot_start == slot_cursor
                    ).first()

                    if not existing:
                        slot = Slot(
                            doctor_id=doctor_id,
                            hospital_id=hospital_id,
                            slot_start=slot_cursor,
                            slot_end=slot_end,
                            status="blocked" if is_blocked else "available"
                        )
                        db.add(slot)
                        slots_created += 1

                    slot_cursor = slot_end

        curr_date += timedelta(days=1)

    db.commit()
    return slots_created

def get_slots_for_doctor(
    doctor_id: str,
    hospital_id: Optional[str],
    target_date: date,
    db: Session,
    auto_generate: bool = True
) -> List[Slot]:
    """
    Retrieves slots for a doctor on a specific date.
    Auto-generates from template if none exist.
    """
    # UTC range covering the target date in IST
    start_of_day_ist = datetime.combine(target_date, time(0, 0), tzinfo=IST_ZONE)
    end_of_day_ist = datetime.combine(target_date, time(23, 59, 59), tzinfo=IST_ZONE)

    start_utc = start_of_day_ist.astimezone(timezone.utc)
    end_utc = end_of_day_ist.astimezone(timezone.utc)

    query = db.query(Slot).filter(
        Slot.doctor_id == doctor_id,
        Slot.slot_start >= start_utc,
        Slot.slot_start <= end_utc
    )
    if hospital_id:
        query = query.filter(Slot.hospital_id == hospital_id)

    slots = query.order_by(Slot.slot_start).all()

    # If no slots found and auto_generate is enabled, generate for this doctor
    if not slots and auto_generate:
        # Determine hospital if not specified
        target_hospital_id = hospital_id
        if not target_hospital_id:
            aff = db.query(DoctorHospital).filter(
                DoctorHospital.doctor_id == doctor_id,
                DoctorHospital.is_active == True
            ).first()
            if aff:
                target_hospital_id = aff.hospital_id

        if target_hospital_id:
            generate_slots_for_doctor(doctor_id, target_hospital_id, target_date, target_date, db)
            slots = query.order_by(Slot.slot_start).all()

    return slots
