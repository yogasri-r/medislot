import pytest
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta, date
from fastapi.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.doctor import Doctor
from app.models.hospital import Hospital
from app.models.schedule import Slot
from app.models.appointment import Appointment, ReminderJob, Notification, Waitlist
from app.models.patient import Patient
from app.models.user import User
from app.services.email import email_sender
from app.services.reminder import (
    generate_signed_reminder_token,
    verify_signed_reminder_token,
    process_pending_reminders,
    check_high_risk_no_show
)

client = TestClient(app)

def get_auth_token(email: str, password: str = "Patient@123456") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]

def get_admin_token() -> str:
    res = client.post("/api/v1/auth/login", json={"email": "admin@medislot.com", "password": "Admin@123456"})
    assert res.status_code == 200, f"Super Admin login failed: {res.text}"
    return res.json()["access_token"]

def get_doctor_token(email: str = "doctor1@medislot.com") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Doctor@123456"})
    assert res.status_code == 200, f"Doctor login failed: {res.text}"
    return res.json()["access_token"]

# ---------------------------------------------------------------------------
# Test 1: Signed Token Cryptographic Integrity & Expiration
# ---------------------------------------------------------------------------

def test_signed_token_generation_and_tamper_protection():
    appt_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    future_exp = datetime.now(timezone.utc) + timedelta(hours=24)

    # 1. Valid token generation and round-trip verification
    token = generate_signed_reminder_token(appt_id, job_id, future_exp)
    res_appt_id, res_job_id, res_exp = verify_signed_reminder_token(token)
    assert res_appt_id == appt_id
    assert res_job_id == job_id
    assert int(res_exp.timestamp()) == int(future_exp.timestamp())

    # 2. Tampered appointment_id must fail
    tampered_parts = token.split(":")
    tampered_parts[0] = str(uuid.uuid4())
    tampered_token = ":".join(tampered_parts)
    with pytest.raises(Exception) as exc_info:
        verify_signed_reminder_token(tampered_token)
    assert "Invalid or tampered" in str(exc_info.value)

    # 3. Tampered signature must fail
    tampered_sig_token = token[:-4] + "ffff"
    with pytest.raises(Exception) as exc_info:
        verify_signed_reminder_token(tampered_sig_token)
    assert "Invalid or tampered" in str(exc_info.value)

    # 4. Expired token must fail
    past_exp = datetime.now(timezone.utc) - timedelta(minutes=5)
    expired_token = generate_signed_reminder_token(appt_id, job_id, past_exp)
    with pytest.raises(Exception) as exc_info:
        verify_signed_reminder_token(expired_token)
    assert "expired" in str(exc_info.value).lower()

# ---------------------------------------------------------------------------
# Test 2: Booking Confirmation Dispatch & Future Reminder Scheduling
# ---------------------------------------------------------------------------

def test_booking_confirmation_and_reminder_scheduling():
    email_sender.clear()
    db = SessionLocal()
    doc = db.query(Doctor).first()
    db.close()

    # Find next available weekday slot
    slot = None
    for day_offset in range(3, 20):
        target_date = date.today() + timedelta(days=day_offset)
        if target_date.weekday() >= 5:
            continue
        slots_res = client.get(f"/api/v1/slots?doctor_id={doc.id}&target_date={target_date.isoformat()}")
        avail = [s for s in slots_res.json() if s["status"] == "available"]
        if avail:
            slot = avail[0]
            break

    assert slot is not None, "Need an available weekday slot"

    # Book as patient 10
    pat_token = get_auth_token("patient10@medislot.com")
    book_res = client.post("/api/v1/appointments", json={
        "slot_id": slot["id"],
        "appointment_type": "new_patient",
        "notes": "Testing confirmation and reminders"
    }, headers={"Authorization": f"Bearer {pat_token}"})
    assert book_res.status_code == 201, f"Booking failed: {book_res.text}"
    appt_data = book_res.json()

    # 1. Verify immediate booking confirmation email was dispatched
    sent = email_sender.get_emails_for_recipient("patient10@medislot.com")
    assert len(sent) >= 1
    conf_email = sent[-1]
    assert "Appointment Confirmed" in conf_email.subject
    assert appt_data["appointment_number"] in conf_email.body_text
    assert "reminders/respond?token=" in conf_email.body_text

    # 2. Verify reminder_jobs were scheduled in database (24h and 2h)
    db = SessionLocal()
    jobs = db.query(ReminderJob).filter(ReminderJob.appointment_id == appt_data["id"]).all()
    job_types = [j.reminder_type for j in jobs]
    assert "reminder_24h" in job_types
    assert "reminder_2h" in job_types

    for j in jobs:
        assert j.status == "scheduled"
        assert j.execution_count == 0
        assert j.is_responded is False
        assert j.confirmation_token is not None

    db.close()

# ---------------------------------------------------------------------------
# Test 3: One-Click Confirm Attendance (Direct Email Link)
# ---------------------------------------------------------------------------

def test_one_click_confirm_attendance():
    db = SessionLocal()
    # Find an appointment with a scheduled reminder job
    job = db.query(ReminderJob).filter(
        ReminderJob.reminder_type == "reminder_24h",
        ReminderJob.is_responded == False
    ).first()
    assert job is not None
    token = job.confirmation_token
    appt_id = job.appointment_id
    db.close()

    # Call GET /reminders/respond?token=...&action=confirmed
    res = client.get(f"/api/v1/reminders/respond?token={token}&action=confirmed")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "confirmed"
    assert "attendance has been confirmed" in data["message"].lower()

    # Verify database state
    db = SessionLocal()
    updated_job = db.query(ReminderJob).filter(ReminderJob.id == job.id).first()
    assert updated_job.is_responded is True
    assert updated_job.response_action == "confirmed"
    db.close()

    # IDEMPOTENCY: Calling it again returns already_recorded status without error
    repeat_res = client.get(f"/api/v1/reminders/respond?token={token}&action=confirmed")
    assert repeat_res.status_code == 200
    repeat_data = repeat_res.json()
    assert repeat_data["status"] == "already_recorded"

# ---------------------------------------------------------------------------
# Test 4: One-Click Cancel Appointment & Waitlist Auto-Offer
# ---------------------------------------------------------------------------

def test_one_click_cancel_frees_slot_and_triggers_waitlist():
    db = SessionLocal()
    doc = db.query(Doctor).first()
    hosp = db.query(Hospital).first()
    patient_wait = db.query(Patient).filter(Patient.user.has(email="patient30@medislot.com")).first()
    db.close()

    target_date = date.today() + timedelta(days=8)

    # 1. Put patient30 on waitlist for target_date
    wait_token = get_auth_token("patient30@medislot.com")
    client.post("/api/v1/waitlist", json={
        "doctor_id": doc.id,
        "hospital_id": hosp.id,
        "preferred_date": target_date.isoformat(),
        "preferred_time_range": "morning"
    }, headers={"Authorization": f"Bearer {wait_token}"})

    # 2. Book appointment as patient11
    slots = client.get(f"/api/v1/slots?doctor_id={doc.id}&target_date={target_date.isoformat()}").json()
    avail = [s for s in slots if s["status"] == "available"]
    assert len(avail) > 0
    slot = avail[0]

    pat11_token = get_auth_token("patient11@medislot.com")
    book_res = client.post("/api/v1/appointments", json={
        "slot_id": slot["id"],
        "appointment_type": "new_patient"
    }, headers={"Authorization": f"Bearer {pat11_token}"})
    appt_id = book_res.json()["id"]

    # 3. Retrieve reminder job for patient11
    db = SessionLocal()
    job = db.query(ReminderJob).filter(
        ReminderJob.appointment_id == appt_id,
        ReminderJob.reminder_type == "reminder_24h"
    ).first()
    assert job is not None
    token = job.confirmation_token
    db.close()

    # 4. Patient 11 clicks one-click cancel in email
    cancel_res = client.get(f"/api/v1/reminders/respond?token={token}&action=cancelled")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # 5. Verify appointment is cancelled and underlying slot is available/offered
    db = SessionLocal()
    cancelled_appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    assert cancelled_appt.status == "cancelled"

    # 6. Verify waitlist auto-offer was triggered for patient30
    wait_entry = db.query(Waitlist).filter(
        Waitlist.patient_id == patient_wait.id,
        Waitlist.doctor_id == doc.id,
        Waitlist.preferred_date == target_date
    ).first()
    assert wait_entry.status == "offered"
    assert wait_entry.offered_slot_id == slot["id"]
    db.close()

# ---------------------------------------------------------------------------
# Test 5: Worker Idempotency (Retries Never Send Duplicate Reminders)
# ---------------------------------------------------------------------------

def test_reminder_worker_idempotency():
    email_sender.clear()
    db = SessionLocal()

    # Query doctor, hospital, patient
    doc = db.query(Doctor).first()
    hosp = db.query(Hospital).first()
    pat = db.query(Patient).filter(Patient.user.has(email="patient15@medislot.com")).first()

    # Create a dedicated past slot and test appointment
    past_start = datetime.now(timezone.utc) - timedelta(hours=5)
    dummy_slot = Slot(
        doctor_id=doc.id,
        hospital_id=hosp.id,
        slot_start=past_start,
        slot_end=past_start + timedelta(minutes=20),
        status="booked"
    )
    db.add(dummy_slot)
    db.flush()

    appt = Appointment(
        appointment_number=f"MED-TEST-{uuid.uuid4().hex[:6].upper()}",
        slot_id=dummy_slot.id,
        doctor_id=doc.id,
        hospital_id=hosp.id,
        patient_id=pat.id,
        appointment_type="follow_up",
        status="booked"
    )
    db.add(appt)
    db.flush()

    past_scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    job_id = f"test-idem-{uuid.uuid4().hex[:8]}"
    token = generate_signed_reminder_token(appt.id, job_id, datetime.now(timezone.utc) + timedelta(hours=2))

    job = ReminderJob(
        id=job_id,
        appointment_id=appt.id,
        reminder_type="reminder_24h",
        scheduled_for=past_scheduled_time,
        status="scheduled",
        confirmation_token=token,
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        is_responded=False,
        execution_count=0
    )
    db.add(job)
    db.commit()

    # First execution: worker processes the job
    count1 = process_pending_reminders(db)
    assert count1 >= 1

    # Verify email was dispatched
    emails1 = email_sender.get_emails_for_recipient("patient15@medislot.com")
    assert len(emails1) == 1

    # Verify job transitioned to completed with execution_count = 1
    db.refresh(job)
    assert job.status == "completed"
    assert job.execution_count == 1

    # SECOND EXECUTION (Simulating scheduler retry or duplicate tick)
    count2 = process_pending_reminders(db)
    # Must NOT dispatch duplicate email
    emails2 = email_sender.get_emails_for_recipient("patient15@medislot.com")
    assert len(emails2) == 1, "Duplicate reminder must NEVER be sent on retries!"

    db.refresh(job)
    assert job.execution_count == 1
    db.close()

# ---------------------------------------------------------------------------
# Test 6: Doctor Schedule Delay Alerts Broadcasting
# ---------------------------------------------------------------------------

def test_doctor_delay_alerts_broadcasting():
    email_sender.clear()
    db = SessionLocal()
    doc = db.query(Doctor).first()
    hosp = db.query(Hospital).first()
    db.close()

    # Book an appointment today for patient16 with doc
    now = datetime.now(timezone.utc)
    # Find or create a slot for today
    db = SessionLocal()
    slot_today = Slot(
        doctor_id=doc.id,
        hospital_id=hosp.id,
        slot_start=now + timedelta(hours=3),
        slot_end=now + timedelta(hours=3, minutes=20),
        status="booked"
    )
    db.add(slot_today)
    db.flush()

    pat16 = db.query(Patient).filter(Patient.user.has(email="patient16@medislot.com")).first()
    appt_today = Appointment(
        appointment_number=f"MED-DELAY-{uuid.uuid4().hex[:6].upper()}",
        slot_id=slot_today.id,
        doctor_id=doc.id,
        hospital_id=hosp.id,
        patient_id=pat16.id,
        appointment_type="new_patient",
        status="booked",
        estimated_wait_minutes=10
    )
    db.add(appt_today)
    db.commit()
    appt_id = str(appt_today.id)
    db.close()

    # Super Admin triggers 25-minute delay alert for doc
    admin_token = get_admin_token()
    delay_res = client.post("/api/v1/reminders/doctor-delay", json={
        "doctor_id": doc.id,
        "hospital_id": hosp.id,
        "delay_minutes": 25
    }, headers={"Authorization": f"Bearer {admin_token}"})

    assert delay_res.status_code == 200
    data = delay_res.json()
    assert data["status"] == "success"
    assert data["alerted_patients_count"] >= 1

    # Verify email was dispatched with delay guidance
    emails = email_sender.get_emails_for_recipient("patient16@medislot.com")
    assert len(emails) >= 1
    delay_email = [e for e in emails if "Schedule Update" in e.subject][0]
    assert "25 minutes" in delay_email.body_text
    assert "arriving 25 minutes after" in delay_email.body_text

    # Verify updated estimated wait time
    db = SessionLocal()
    updated_appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    assert updated_appt.estimated_wait_minutes == 35  # 10 initial + 25 delay
    db.close()

# ---------------------------------------------------------------------------
# Test 7: ML High No-Show Risk Stub Hook
# ---------------------------------------------------------------------------

def test_high_no_show_risk_stub_hook():
    db = SessionLocal()
    doc = db.query(Doctor).first()
    
    # Find a patient with 0 past unfulfilled appointments, or create a clean one
    pat = db.query(Patient).filter(
        ~Patient.appointments.any(Appointment.status.in_(["cancelled", "no_show"]))
    ).first()
    if not pat:
        clean_user = User(
            email=f"clean_{uuid.uuid4().hex[:8]}@medislot.com",
            password_hash="test_hash",
            full_name="Clean Patient",
            phone=f"+9199{uuid.uuid4().int % 100000000:08d}",
            role="patient"
        )
        db.add(clean_user)
        db.flush()
        pat = Patient(user_id=clean_user.id)
        db.add(pat)
        db.commit()

    # Case A: Future slot with short lead time and 0 cancellations -> False
    slot_short = Slot(
        doctor_id=doc.id,
        hospital_id=doc.hospitals[0].hospital_id,
        slot_start=datetime.now(timezone.utc) + timedelta(days=2),
        slot_end=datetime.now(timezone.utc) + timedelta(days=2, minutes=20)
    )
    appt_normal = Appointment(patient_id=pat.id, slot=slot_short)
    assert check_high_risk_no_show(appt_normal, db) is False

    # Case B: Slot with high lead time (> 14 days) -> True
    slot_far = Slot(
        doctor_id=doc.id,
        hospital_id=doc.hospitals[0].hospital_id,
        slot_start=datetime.now(timezone.utc) + timedelta(days=20),
        slot_end=datetime.now(timezone.utc) + timedelta(days=20, minutes=20)
    )
    appt_high_lead = Appointment(patient_id=pat.id, slot=slot_far)
    assert check_high_risk_no_show(appt_high_lead, db) is True
    db.close()
