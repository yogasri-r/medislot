import hmac
import hashlib
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.appointment import Appointment, ReminderJob, Notification
from app.models.schedule import Slot
from app.models.patient import Patient
from app.models.doctor import Doctor, DoctorHospital
from app.models.hospital import Hospital
from app.models.user import User
from app.services.email import email_sender
from app.services.availability import convert_utc_to_ist_str
from app.core.dependencies import log_audit

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def get_doctor_display_name(doctor: Optional[Doctor]) -> str:
    """Formats doctor name cleanly, avoiding 'Dr. Dr.' duplication."""
    if not doctor or not doctor.user:
        return "Doctor"
    name = doctor.user.full_name.strip()
    if name.lower().startswith("dr.") or name.lower().startswith("dr "):
        return name
    return f"Dr. {name}"

# ---------------------------------------------------------------------------
# Signed One-Click Token Generator and Verifier
# ---------------------------------------------------------------------------

def generate_signed_reminder_token(appointment_id: str, reminder_job_id: str, expires_at: datetime) -> str:
    """
    Generates a tamper-proof HMAC-SHA256 signed token for one-click confirmation/cancellation.
    Format: {appointment_id}:{reminder_job_id}:{exp_timestamp}:{hmac_sig}
    """
    exp_ts = int(expires_at.timestamp())
    payload = f"{appointment_id}:{reminder_job_id}:{exp_ts}"
    signature = hmac.new(settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}:{signature}"

def verify_signed_reminder_token(token: str) -> Tuple[str, str, datetime]:
    """
    Verifies token integrity, signature, and expiration.
    Returns (appointment_id, reminder_job_id, expires_at).
    Raises HTTPException(400) if invalid or expired.
    """
    parts = token.split(":")
    if len(parts) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed confirmation token."
        )

    appointment_id, reminder_job_id, exp_ts_str, provided_sig = parts
    try:
        exp_ts = int(exp_ts_str)
        expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
    except (ValueError, OverflowError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token expiration timestamp."
        )

    # Recompute expected signature
    payload = f"{appointment_id}:{reminder_job_id}:{exp_ts}"
    expected_sig = hmac.new(settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]

    if not hmac.compare_digest(provided_sig, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or tampered confirmation token signature."
        )

    if utc_now() > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This confirmation link has expired. Please manage your appointment via the MediSlot portal."
        )

    return appointment_id, reminder_job_id, expires_at

def build_action_urls(token: str) -> Dict[str, str]:
    """Builds one-click confirm and cancel URLs."""
    base = settings.BASE_URL.rstrip("/")
    api_prefix = settings.API_V1_STR
    return {
        "confirm_url": f"{base}{api_prefix}/reminders/respond?token={token}&action=confirmed",
        "cancel_url": f"{base}{api_prefix}/reminders/respond?token={token}&action=cancelled"
    }

# ---------------------------------------------------------------------------
# ML High No-Show Risk Model Integration
# ---------------------------------------------------------------------------

def check_high_risk_no_show(appointment: Appointment, db: Session) -> bool:
    """
    Production ML No-Show Risk Evaluation:
    Evaluates appointment features via trained Gradient Boosting model.
    Flags proactive reminder intervention when probability >= 0.35 (calibrated alert threshold)
    or when clinical lead time exceeds 14 days.
    """
    slot = appointment.slot
    if not slot:
        return False

    lead_time = max(0.0, (slot.slot_start - utc_now()).total_seconds() / 86400.0)

    try:
        from app.services.ml_service import ml_service
        from app.schemas.ml import NoShowPredictionRequest
        if ml_service.is_ready:
            if appointment.id:
                req = NoShowPredictionRequest(appointment_id=appointment.id)
            else:
                req = NoShowPredictionRequest(
                    lead_time_days=lead_time,
                    appointment_type=appointment.appointment_type or "new_patient"
                )
            res = ml_service.predict_no_show(req, db=db)
            return res.is_high_risk or res.no_show_probability >= 0.35 or lead_time > 14.0
    except Exception as e:
        print(f"[ReminderService] ML model fallback: {e}")

    # Heuristic fallback
    past_unfulfilled = db.query(Appointment).filter(
        Appointment.patient_id == appointment.patient_id,
        Appointment.id != appointment.id,
        Appointment.status.in_(["cancelled", "no_show"])
    ).count()

    return past_unfulfilled >= 2 or lead_time > 14.0

# ---------------------------------------------------------------------------
# Scheduling Engine (Called during booking)
# ---------------------------------------------------------------------------

def schedule_appointment_reminders(appointment: Appointment, db: Session) -> List[ReminderJob]:
    """
    Schedules lifecycle reminders for a newly booked appointment:
    1. Immediate booking confirmation email
    2. 24-hour advance reminder (if scheduled in the future)
    3. 2-hour advance reminder (if scheduled in the future)
    4. High-risk no-show intervention reminder (if flagged by ML stub)
    """
    slot = db.query(Slot).filter(Slot.id == appointment.slot_id).first()
    if not slot:
        return []

    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
    if not patient or not patient.user:
        return []

    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
    hospital = db.query(Hospital).filter(Hospital.id == appointment.hospital_id).first()

    doctor_name = get_doctor_display_name(doctor)
    hospital_name = hospital.name if hospital else "Hospital"
    slot_start_ist = convert_utc_to_ist_str(slot.slot_start)

    now = utc_now()
    slot_start = slot.slot_start
    created_jobs = []

    # 1. Booking Confirmation Email (Dispatched Immediately)
    conf_job_id = f"conf-{appointment.id[:8]}"
    conf_token = generate_signed_reminder_token(appointment.id, conf_job_id, slot_start)
    urls = build_action_urls(conf_token)

    confirmation_subject = f"Appointment Confirmed: MediSlot - {appointment.appointment_number}"
    confirmation_body = f"""
Hello {patient.user.full_name},

Your appointment has been successfully confirmed on MediSlot!

--------------------------------------------------
APPOINTMENT DETAILS:
- Appointment Number : {appointment.appointment_number}
- Doctor             : {doctor_name} ({doctor.specialty if doctor else ''})
- Hospital           : {hospital_name}
- Date & Time (IST)  : {slot_start_ist}
- Appointment Type   : {appointment.appointment_type.replace('_', ' ').title()}
{"- Telemedicine URL   : " + appointment.telemedicine_meeting_url if appointment.telemedicine_meeting_url else ""}
--------------------------------------------------

MANAGE YOUR APPOINTMENT IN ONE CLICK:
- To Confirm Attendance: {urls['confirm_url']}
- To Cancel if Unable to Attend: {urls['cancel_url']}

Thank you for choosing MediSlot.
"Right doctor. Right slot. Less waiting."
"""
    # Send email
    email_sender.send_email(
        to_email=patient.user.email,
        subject=confirmation_subject,
        body_text=confirmation_body
    )

    # Log notification record
    notif = Notification(
        user_id=patient.user_id,
        appointment_id=appointment.id,
        notification_type="booking_confirmation",
        channel="email",
        recipient=patient.user.email,
        title=confirmation_subject,
        body=confirmation_body,
        status="sent",
        sent_at=now
    )
    db.add(notif)

    # 2. 24-Hour Reminder Job
    t_24h = slot_start - timedelta(hours=24)
    if t_24h > now:
        existing_24h = db.query(ReminderJob).filter(
            ReminderJob.appointment_id == appointment.id,
            ReminderJob.reminder_type == "reminder_24h"
        ).first()
        if not existing_24h:
            r24_id = f"r24-{appointment.id[:8]}"
            token_24 = generate_signed_reminder_token(appointment.id, r24_id, slot_start)
            job_24 = ReminderJob(
                id=r24_id,
                appointment_id=appointment.id,
                reminder_type="reminder_24h",
                scheduled_for=t_24h,
                status="scheduled",
                confirmation_token=token_24,
                token_expires_at=slot_start,
                is_responded=False,
                execution_count=0
            )
            db.add(job_24)
            created_jobs.append(job_24)

    # 3. 2-Hour Reminder Job
    t_2h = slot_start - timedelta(hours=2)
    if t_2h > now:
        existing_2h = db.query(ReminderJob).filter(
            ReminderJob.appointment_id == appointment.id,
            ReminderJob.reminder_type == "reminder_2h"
        ).first()
        if not existing_2h:
            r2_id = f"r2-{appointment.id[:8]}"
            token_2 = generate_signed_reminder_token(appointment.id, r2_id, slot_start)
            job_2 = ReminderJob(
                id=r2_id,
                appointment_id=appointment.id,
                reminder_type="reminder_2h",
                scheduled_for=t_2h,
                status="scheduled",
                confirmation_token=token_2,
                token_expires_at=slot_start,
                is_responded=False,
                execution_count=0
            )
            db.add(job_2)
            created_jobs.append(job_2)

    # 4. High No-Show Risk Stub Hook (Phase 5 Model Hook)
    is_high_risk = check_high_risk_no_show(appointment, db)
    if is_high_risk:
        t_high_risk = slot_start - timedelta(hours=12)
        if t_high_risk > now:
            existing_hr = db.query(ReminderJob).filter(
                ReminderJob.appointment_id == appointment.id,
                ReminderJob.reminder_type == "high_risk_extra"
            ).first()
            if not existing_hr:
                rhr_id = f"rhr-{appointment.id[:8]}"
                token_hr = generate_signed_reminder_token(appointment.id, rhr_id, slot_start)
                job_hr = ReminderJob(
                    id=rhr_id,
                    appointment_id=appointment.id,
                    reminder_type="high_risk_extra",
                    scheduled_for=t_high_risk,
                    status="scheduled",
                    confirmation_token=token_hr,
                    token_expires_at=slot_start,
                    is_responded=False,
                    execution_count=0
                )
                db.add(job_hr)
                created_jobs.append(job_hr)

    db.commit()
    return created_jobs

# ---------------------------------------------------------------------------
# Idempotent Worker Engine (Triggered by APScheduler)
# ---------------------------------------------------------------------------

def process_pending_reminders(db: Session) -> int:
    """
    Executes all scheduled reminder jobs whose scheduled time has passed.
    IDEMPOTENCY INVARIANTS:
    - Retries never send duplicate communications (checks status and execution_count).
    - Automatically cancels reminders for already cancelled/completed appointments.
    - Transitions jobs: scheduled -> processing -> completed.
    """
    now = utc_now()
    pending_jobs = db.query(ReminderJob).filter(
        ReminderJob.status == "scheduled",
        ReminderJob.scheduled_for <= now
    ).all()

    processed_count = 0

    for job in pending_jobs:
        # Check appointment status
        appt = db.query(Appointment).filter(Appointment.id == job.appointment_id).first()
        if not appt or appt.status in ["cancelled", "completed", "no_show"]:
            job.status = "cancelled"
            db.commit()
            continue

        # Invariant: prevent duplicate execution
        if job.execution_count > 0:
            job.status = "completed"
            db.commit()
            continue

        # Transition to processing state
        job.status = "processing"
        db.commit()

        # Build message
        patient = appt.patient
        if not patient or not patient.user:
            job.status = "failed"
            db.commit()
            continue

        doctor = appt.doctor
        hospital = appt.hospital
        doctor_name = get_doctor_display_name(doctor)
        hospital_name = hospital.name if hospital else "Hospital"
        slot_start_ist = convert_utc_to_ist_str(appt.slot.slot_start) if appt.slot else "Scheduled Time"

        urls = build_action_urls(job.confirmation_token)

        if job.reminder_type == "reminder_24h":
            subject = f"Reminder: Your consultation with {doctor_name} is tomorrow"
            body = f"""
Hello {patient.user.full_name},

This is a reminder that your appointment with {doctor_name} at {hospital_name} is scheduled for tomorrow at {slot_start_ist}.

Appointment Number: {appt.appointment_number}

Will you be able to make it?
- CONFIRM ATTENDANCE: {urls['confirm_url']}
- CANCEL & FREE SLOT : {urls['cancel_url']}

Confirming early helps other waiting patients!
"""
        elif job.reminder_type == "reminder_2h":
            # Lookup OPD room number
            aff = db.query(DoctorHospital).filter(
                DoctorHospital.doctor_id == appt.doctor_id,
                DoctorHospital.hospital_id == appt.hospital_id
            ).first()
            room_info = f"Room: {aff.room_number}" if (aff and aff.room_number) else "Main OPD Reception"

            subject = f"Upcoming Consultation in 2 Hours - {doctor_name}"
            body = f"""
Hello {patient.user.full_name},

Your appointment with {doctor_name} at {hospital_name} starts in 2 hours ({slot_start_ist}).
Location: {room_info}

Please plan to arrive 10 minutes prior for check-in.
- CANCEL APPOINTMENT: {urls['cancel_url']}
"""
        elif job.reminder_type == "high_risk_extra":
            subject = f"Action Required: Confirm your appointment with {doctor_name}"
            body = f"""
Hello {patient.user.full_name},

Please confirm your upcoming appointment (No: {appt.appointment_number}) with {doctor_name} on {slot_start_ist}.
Due to high clinical demand for this slot, unconfirmed appointments may experience delayed intake.

- PLEASE CONFIRM HERE: {urls['confirm_url']}
- UNABLE TO ATTEND? CANCEL HERE: {urls['cancel_url']}
"""
        else:
            subject = f"MediSlot Appointment Notification - {appt.appointment_number}"
            body = f"Notification regarding your appointment on {slot_start_ist}."

        # Dispatch email
        send_success = email_sender.send_email(
            to_email=patient.user.email,
            subject=subject,
            body_text=body
        )

        # Log notification record
        notif = Notification(
            user_id=patient.user_id,
            appointment_id=appt.id,
            notification_type=job.reminder_type,
            channel="email",
            recipient=patient.user.email,
            title=subject,
            body=body,
            status="sent" if send_success else "failed",
            sent_at=now if send_success else None,
            error_message=None if send_success else "Email dispatch failed"
        )
        db.add(notif)

        # Update job record
        job.status = "completed" if send_success else "failed"
        job.execution_count += 1
        job.last_executed_at = now
        db.commit()

        if send_success:
            processed_count += 1

    return processed_count

# ---------------------------------------------------------------------------
# One-Click Response Action Handler
# ---------------------------------------------------------------------------

def handle_reminder_response(token: str, action: str, db: Session) -> Dict[str, Any]:
    """
    Handles a signed one-click response (confirm or cancel).
    Idempotent: repeating the link safely returns the recorded status.
    """
    if action not in ["confirmed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be either 'confirmed' or 'cancelled'."
        )

    appointment_id, reminder_job_id, _ = verify_signed_reminder_token(token)

    # Locate reminder job
    job = db.query(ReminderJob).filter(ReminderJob.confirmation_token == token).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder confirmation record not found."
        )

    appt = db.query(Appointment).filter(Appointment.id == job.appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated appointment not found.")

    # Idempotency check: already responded
    if job.is_responded:
        return {
            "status": "already_recorded",
            "message": f"Your response ('{job.response_action}') was already recorded previously.",
            "appointment_number": appt.appointment_number,
            "appointment_status": appt.status
        }

    # Execute action
    if action == "confirmed":
        job.is_responded = True
        job.response_action = "confirmed"
        db.commit()

        log_audit(
            db=db,
            user_id=appt.patient.user_id if (appt.patient and appt.patient.user) else None,
            action="CONFIRM_APPOINTMENT_REMINDER",
            resource_type="appointment",
            resource_id=appt.id,
            hospital_id=appt.hospital_id,
            details={"appointment_number": appt.appointment_number, "reminder_type": job.reminder_type}
        )

        return {
            "status": "confirmed",
            "message": "Thank you! Your attendance has been confirmed for this appointment.",
            "appointment_number": appt.appointment_number,
            "appointment_status": appt.status
        }

    else:  # action == "cancelled"
        job.is_responded = True
        job.response_action = "cancelled"

        # Cancel appointment and free slot (reuses robust cancellation service)
        from app.services.booking import cancel_appointment as svc_cancel
        patient_user = appt.patient.user if (appt.patient and appt.patient.user) else None

        if appt.status not in ["cancelled", "completed"]:
            svc_cancel(
                appointment_id=appt.id,
                reason="Cancelled by patient via one-click email confirmation",
                current_user=patient_user,
                db=db
            )

        db.commit()

        return {
            "status": "cancelled",
            "message": "Your appointment has been cancelled successfully. The slot has been released.",
            "appointment_number": appt.appointment_number,
            "appointment_status": "cancelled"
        }

# ---------------------------------------------------------------------------
# Cancellation, Reschedule & Delay Alerts
# ---------------------------------------------------------------------------

def send_cancellation_alert(appointment: Appointment, reason: str, db: Session):
    """
    Dispatches cancellation notification and cancels all pending reminder jobs.
    """
    # 1. Cancel pending reminder jobs
    pending_jobs = db.query(ReminderJob).filter(
        ReminderJob.appointment_id == appointment.id,
        ReminderJob.status == "scheduled"
    ).all()
    for j in pending_jobs:
        j.status = "cancelled"
    db.commit()

    # 2. Dispatch cancellation email to patient
    patient = appointment.patient
    if patient and patient.user:
        doctor_name = appointment.doctor.user.full_name if (appointment.doctor and appointment.doctor.user) else "Doctor"
        slot_ist = convert_utc_to_ist_str(appointment.slot.slot_start) if appointment.slot else "Scheduled Time"

        subject = f"Appointment Cancelled: MediSlot - {appointment.appointment_number}"
        body = f"""
Hello {patient.user.full_name},

Your appointment (No: {appointment.appointment_number}) with Dr. {doctor_name} scheduled for {slot_ist} has been cancelled.

Reason for cancellation: {reason}

If you would like to reschedule or book a new slot, please visit MediSlot.
"""
        email_sender.send_email(
            to_email=patient.user.email,
            subject=subject,
            body_text=body
        )

        notif = Notification(
            user_id=patient.user_id,
            appointment_id=appointment.id,
            notification_type="cancellation_alert",
            channel="email",
            recipient=patient.user.email,
            title=subject,
            body=body,
            status="sent",
            sent_at=utc_now()
        )
        db.add(notif)
        db.commit()

def send_reschedule_alert(appointment: Appointment, old_slot: Slot, new_slot: Slot, db: Session):
    """
    Dispatches reschedule notification, cancels old reminder jobs, and sets up new ones.
    """
    # 1. Cancel old pending reminders
    old_jobs = db.query(ReminderJob).filter(
        ReminderJob.appointment_id == appointment.id,
        ReminderJob.status == "scheduled"
    ).all()
    for j in old_jobs:
        j.status = "cancelled"
    db.commit()

    # 2. Schedule new reminders for new slot
    schedule_appointment_reminders(appointment, db)

    # 3. Dispatch reschedule notice
    patient = appointment.patient
    if patient and patient.user:
        doctor_name = appointment.doctor.user.full_name if (appointment.doctor and appointment.doctor.user) else "Doctor"
        old_time_ist = convert_utc_to_ist_str(old_slot.slot_start)
        new_time_ist = convert_utc_to_ist_str(new_slot.slot_start)

        subject = f"Appointment Rescheduled: MediSlot - {appointment.appointment_number}"
        body = f"""
Hello {patient.user.full_name},

Your appointment (No: {appointment.appointment_number}) with Dr. {doctor_name} has been rescheduled.

- PREVIOUS TIME : {old_time_ist}
- NEW TIME (IST): {new_time_ist}

Thank you for your flexibility!
"""
        email_sender.send_email(
            to_email=patient.user.email,
            subject=subject,
            body_text=body
        )

        notif = Notification(
            user_id=patient.user_id,
            appointment_id=appointment.id,
            notification_type="reschedule_alert",
            channel="email",
            recipient=patient.user.email,
            title=subject,
            body=body,
            status="sent",
            sent_at=utc_now()
        )
        db.add(notif)
        db.commit()

def send_doctor_delay_alerts(
    doctor_id: str,
    hospital_id: str,
    delay_minutes: int,
    db: Session
) -> int:
    """
    Alerts all upcoming patients in the doctor's queue when a doctor is running behind schedule.
    Updates estimated wait times and advises adjusted arrival times.
    """
    now = utc_now()
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)

    # Find active upcoming appointments today
    appointments = db.query(Appointment).join(Slot).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.hospital_id == hospital_id,
        Appointment.status.in_(["booked", "checked_in"]),
        Slot.slot_start >= now,
        Slot.slot_start < today_end
    ).order_by(Slot.slot_start.asc()).all()

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    doctor_name = get_doctor_display_name(doctor)
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    hospital_name = hospital.name if hospital else "Hospital"

    alerted_count = 0
    for appt in appointments:
        appt.estimated_wait_minutes = (appt.estimated_wait_minutes or 0) + delay_minutes

        patient = appt.patient
        if patient and patient.user:
            slot_ist = convert_utc_to_ist_str(appt.slot.slot_start)

            subject = f"Schedule Update: {doctor_name} is running ~{delay_minutes} mins behind"
            body = f"""
Hello {patient.user.full_name},

We want to respect your time. {doctor_name} at {hospital_name} is currently experiencing unexpected delays and is running approximately {delay_minutes} minutes behind schedule.

- Scheduled Slot Time : {slot_ist}
- Estimated Delay     : {delay_minutes} minutes

To minimize your waiting room time, we recommend arriving {delay_minutes} minutes after your originally scheduled check-in time.

We apologize for the inconvenience and appreciate your understanding.
"""
            email_sender.send_email(
                to_email=patient.user.email,
                subject=subject,
                body_text=body
            )

            notif = Notification(
                user_id=patient.user_id,
                appointment_id=appt.id,
                notification_type="doctor_delay_alert",
                channel="email",
                recipient=patient.user.email,
                title=subject,
                body=body,
                status="sent",
                sent_at=now
            )
            db.add(notif)
            alerted_count += 1

    db.commit()
    return alerted_count
