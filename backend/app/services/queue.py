from datetime import datetime, timezone, timedelta, date, time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.appointment import Appointment
from app.models.schedule import Slot
from app.models.doctor import Doctor
from app.models.hospital import Hospital
from app.models.patient import Patient
from app.services.availability import convert_utc_to_ist_str, IST_ZONE
from app.schemas.queue import QueueStatusOut, DoctorDailyQueueOut, DoctorDailyQueuePatient

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def get_appointment_queue_status(appointment_id: str, db: Session) -> QueueStatusOut:
    """
    Computes dynamic live queue position and wait time estimate for a patient's appointment:
    - Calculates patients ahead in the queue.
    - Incorporates per-doctor historical consultation duration average.
    - Incorporates live clinic delays and active consultation progress.
    """
    appt = db.query(Appointment).options(
        joinedload(Appointment.slot),
        joinedload(Appointment.doctor),
        joinedload(Appointment.hospital)
    ).filter(Appointment.id == appointment_id).first()

    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    doctor = appt.doctor
    hospital = appt.hospital
    doctor_name = doctor.user.full_name if (doctor and doctor.user) else "Doctor"
    hospital_name = hospital.name if hospital else "Hospital"

    # Historical average consultation duration for this doctor
    avg_duration = db.query(
        func.avg(Appointment.actual_duration_minutes)
    ).filter(
        Appointment.doctor_id == appt.doctor_id,
        Appointment.status == "completed"
    ).scalar()

    historical_avg = round(float(avg_duration), 1) if avg_duration else 18.0

    # Target date in IST
    slot_utc = appt.slot.slot_start if appt.slot else appt.created_at
    slot_ist = slot_utc.astimezone(IST_ZONE)
    target_date = slot_ist.date()

    start_of_day_utc = datetime.combine(target_date, time(0, 0), tzinfo=IST_ZONE).astimezone(timezone.utc)
    end_of_day_utc = datetime.combine(target_date, time(23, 59, 59), tzinfo=IST_ZONE).astimezone(timezone.utc)

    # All appointments for this doctor & hospital on that day
    day_appts = db.query(Appointment).join(Slot).filter(
        Appointment.doctor_id == appt.doctor_id,
        Appointment.hospital_id == appt.hospital_id,
        Slot.slot_start >= start_of_day_utc,
        Slot.slot_start <= end_of_day_utc
    ).order_by(Slot.slot_start.asc()).all()

    # Determine queue number (1-indexed)
    queue_number = 1
    for idx, a in enumerate(day_appts):
        if a.id == appt.id:
            queue_number = idx + 1
            break

    # Determine active consultation and patients ahead
    active_appt = None
    patients_ahead = 0
    for a in day_appts:
        if a.status == "in_consultation":
            active_appt = a
        if a.id == appt.id:
            break
        if a.status in ["booked", "checked_in", "in_consultation"]:
            patients_ahead += 1

    current_consultation_num = active_appt.appointment_number if active_appt else None

    # Check live delay offset
    now = utc_now()
    live_delay = 0

    if active_appt and active_appt.consultation_start_time:
        elapsed = (now - active_appt.consultation_start_time).total_seconds() / 60.0
        if elapsed > historical_avg:
            live_delay = int(elapsed - historical_avg)

    # If slot time has already passed and consultation hasn't started
    if appt.slot and now > appt.slot.slot_start and appt.status in ["booked", "checked_in"]:
        delay_since_slot = int((now - appt.slot.slot_start).total_seconds() / 60.0)
        live_delay = max(live_delay, delay_since_slot)

    # Calculate wait time range
    if appt.status == "in_consultation":
        min_wait = 0
        max_wait = 0
        formatted = "In consultation right now"
    elif appt.status == "completed":
        min_wait = 0
        max_wait = 0
        formatted = "Consultation completed"
    elif appt.status in ["cancelled", "no_show"]:
        min_wait = 0
        max_wait = 0
        formatted = appt.status.replace("_", " ").title()
    elif patients_ahead == 0:
        min_wait = 0
        max_wait = 5
        formatted = "Next in line (0–5 mins)"
    else:
        min_wait = max(5, int(patients_ahead * (historical_avg - 4) + live_delay))
        max_wait = max(min_wait + 8, int(patients_ahead * (historical_avg + 4) + live_delay))
        formatted = f"{min_wait}–{max_wait} mins"

    expected_time = now + timedelta(minutes=(min_wait + max_wait) / 2)
    expected_ist_str = convert_utc_to_ist_str(expected_time)

    return QueueStatusOut(
        appointment_id=appt.id,
        appointment_number=appt.appointment_number,
        doctor_id=appt.doctor_id,
        doctor_name=doctor_name,
        hospital_name=hospital_name,
        status=appt.status,
        queue_number=queue_number,
        patients_ahead=patients_ahead,
        current_consultation_number=current_consultation_num,
        historical_avg_duration_minutes=historical_avg,
        live_delay_minutes=live_delay,
        estimated_wait_minutes_min=min_wait,
        estimated_wait_minutes_max=max_wait,
        estimated_wait_formatted=formatted,
        expected_consultation_time_ist=expected_ist_str
    )

def get_doctor_daily_queue(
    doctor_id: str,
    hospital_id: str,
    target_date: date,
    db: Session
) -> DoctorDailyQueueOut:
    """
    Returns clinical outpatient daily queue for doctor and clinic staff.
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found.")

    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found.")

    start_of_day_utc = datetime.combine(target_date, time(0, 0), tzinfo=IST_ZONE).astimezone(timezone.utc)
    end_of_day_utc = datetime.combine(target_date, time(23, 59, 59), tzinfo=IST_ZONE).astimezone(timezone.utc)

    appts = db.query(Appointment).join(Slot).options(
        joinedload(Appointment.slot),
        joinedload(Appointment.patient).joinedload(Patient.user)
    ).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.hospital_id == hospital_id,
        Slot.slot_start >= start_of_day_utc,
        Slot.slot_start <= end_of_day_utc
    ).order_by(Slot.slot_start.asc()).all()

    patient_records = []
    completed_cnt = 0
    in_consult_cnt = 0
    waiting_cnt = 0

    now = utc_now()
    current_delay = 0

    for idx, a in enumerate(appts):
        if a.status == "completed":
            completed_cnt += 1
        elif a.status == "in_consultation":
            in_consult_cnt += 1
            if a.consultation_start_time:
                elapsed = (now - a.consultation_start_time).total_seconds() / 60.0
                if elapsed > 20:
                    current_delay = int(elapsed - 20)
        elif a.status in ["booked", "checked_in"]:
            waiting_cnt += 1

        p_name = a.patient.user.full_name if (a.patient and a.patient.user) else "Patient"
        p_phone = a.patient.user.phone if (a.patient and a.patient.user) else ""
        time_ist = convert_utc_to_ist_str(a.slot.slot_start) if a.slot else ""

        patient_records.append(DoctorDailyQueuePatient(
            appointment_id=a.id,
            appointment_number=a.appointment_number,
            patient_name=p_name,
            patient_phone=p_phone,
            appointment_type=a.appointment_type,
            status=a.status,
            slot_time_ist=time_ist,
            queue_number=idx + 1,
            check_in_time=a.check_in_time,
            consultation_start_time=a.consultation_start_time,
            estimated_duration_minutes=a.estimated_duration_minutes,
            actual_duration_minutes=a.actual_duration_minutes
        ))

    doctor_name = doctor.user.full_name if doctor.user else "Doctor"

    return DoctorDailyQueueOut(
        doctor_id=doctor.id,
        doctor_name=doctor_name,
        hospital_id=hospital.id,
        hospital_name=hospital.name,
        target_date=target_date.isoformat(),
        total_appointments=len(appts),
        completed_count=completed_cnt,
        in_consultation_count=in_consult_cnt,
        waiting_count=waiting_cnt,
        current_delay_minutes=current_delay,
        patients=patient_records
    )
