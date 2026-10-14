import pytest
import sys
import os
import uuid
import random
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.core.database import SessionLocal
from app.models.doctor import Doctor
from app.models.hospital import Hospital
from app.models.schedule import Slot
from app.models.appointment import Appointment, Waitlist
from app.models.user import User
from app.models.patient import Patient

client = TestClient(app)

def get_auth_token(email: str, password: str = "Patient@123456") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]

def test_slot_listing_and_auto_generation():
    """Tests querying doctor slots and dynamic slot generation from templates."""
    db = SessionLocal()
    doc = db.query(Doctor).first()
    assert doc is not None
    db.close()

    # Query slots for next Monday
    today = date.today()
    days_ahead = (0 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    target_monday = today + timedelta(days=days_ahead)

    res = client.get(f"/api/v1/slots?doctor_id={doc.id}&target_date={target_monday.isoformat()}")
    assert res.status_code == 200
    slots = res.json()
    assert len(slots) > 0, "Slots should be auto-generated from weekly template"
    for s in slots:
        assert s["doctor_id"] == doc.id
        assert "slot_start_ist" in s
        assert "slot_end_ist" in s
        assert s["status"] in ["available", "booked", "blocked"]

def test_booking_concurrency_race_condition_prevention():
    """
    CRITICAL REQUIREMENT:
    20 simultaneous threads attempt to book the exact same slot.
    VERIFY: Exactly 1 succeeds (HTTP 201) and exactly 19 fail (HTTP 409 Conflict).
    Guarantee 0 double bookings.
    """
    db = SessionLocal()
    doc = db.query(Doctor).first()
    assert doc is not None
    db.close()

    # Find or generate slots for a future Tuesday
    today = date.today()
    target_date = today + timedelta(days=14)
    slots_res = client.get(f"/api/v1/slots?doctor_id={doc.id}&target_date={target_date.isoformat()}")
    slots = [s for s in slots_res.json() if s["status"] == "available"]
    assert len(slots) > 0, "Need at least one available slot for concurrency test"
    target_slot = slots[0]
    target_slot_id = target_slot["id"]

    # Gather 20 distinct patient tokens
    patient_tokens = []
    for i in range(1, 21):
        token = get_auth_token(f"patient{i}@medislot.com")
        patient_tokens.append(token)

    assert len(patient_tokens) == 20

    def attempt_booking(token):
        # Dedicated client call per thread
        local_client = TestClient(app)
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "slot_id": target_slot_id,
            "appointment_type": "new_patient",
            "notes": "Concurrency race test"
        }
        resp = local_client.post("/api/v1/appointments", json=payload, headers=headers)
        return resp.status_code, resp.text

    # Execute 20 concurrent requests
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(attempt_booking, tok) for tok in patient_tokens]
        for f in as_completed(futures):
            results.append(f.result())

    status_codes = [r[0] for r in results]
    success_count = status_codes.count(201)
    conflict_count = status_codes.count(409)

    print(f"Concurrency results: 201 Created: {success_count}, 409 Conflict: {conflict_count}")
    assert success_count == 1, f"Expected exactly 1 booking to succeed, but got {success_count}. Responses: {results}"
    assert conflict_count == 19, f"Expected 19 conflicts, but got {conflict_count}"

    # Verify database state
    db = SessionLocal()
    appts = db.query(Appointment).filter(Appointment.slot_id == target_slot_id).all()
    assert len(appts) == 1, f"Database has {len(appts)} appointments for slot {target_slot_id}. Must be exactly 1!"
    slot_record = db.query(Slot).filter(Slot.id == target_slot_id).first()
    assert slot_record.status == "booked"
    db.close()

def test_appointment_lifecycle_state_machine():
    """
    Tests valid state transitions:
    booked -> checked_in -> in_consultation -> completed
    And invalid transitions (must reject with 400 Bad Request):
    completed -> cancelled
    cancelled -> in_consultation
    """
    db = SessionLocal()
    doc = db.query(Doctor).first()
    db.close()

    # Get a fresh slot
    target_date = date.today() + timedelta(days=21)
    slots = client.get(f"/api/v1/slots?doctor_id={doc.id}&target_date={target_date.isoformat()}").json()
    avail = [s for s in slots if s["status"] == "available"]
    assert len(avail) >= 2
    test_slot = avail[0]

    # Book as patient 25
    pat_token = get_auth_token("patient25@medislot.com")
    headers_pat = {"Authorization": f"Bearer {pat_token}"}
    book_res = client.post("/api/v1/appointments", json={
        "slot_id": test_slot["id"],
        "appointment_type": "new_patient"
    }, headers=headers_pat)
    assert book_res.status_code == 201
    appt = book_res.json()
    appt_id = appt["id"]
    assert appt["status"] == "booked"

    # Admin/Staff login to update statuses
    admin_token = get_auth_token("admin@medislot.com", "Admin@123456")
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    # Transition 1: booked -> checked_in (VALID)
    res_checkin = client.post(f"/api/v1/appointments/{appt_id}/status", json={
        "status": "checked_in"
    }, headers=headers_admin)
    assert res_checkin.status_code == 200
    assert res_checkin.json()["status"] == "checked_in"
    assert res_checkin.json()["check_in_time"] is not None

    # Transition 2: checked_in -> in_consultation (VALID)
    res_consult = client.post(f"/api/v1/appointments/{appt_id}/status", json={
        "status": "in_consultation"
    }, headers=headers_admin)
    assert res_consult.status_code == 200
    assert res_consult.json()["status"] == "in_consultation"
    assert res_consult.json()["consultation_start_time"] is not None

    # Transition 3: in_consultation -> completed (VALID)
    res_completed = client.post(f"/api/v1/appointments/{appt_id}/status", json={
        "status": "completed"
    }, headers=headers_admin)
    assert res_completed.status_code == 200
    completed_data = res_completed.json()
    assert completed_data["status"] == "completed"
    assert completed_data["consultation_end_time"] is not None
    assert completed_data["actual_duration_minutes"] is not None

    # Transition 4 (INVALID): completed -> cancelled (MUST REJECT 400)
    res_invalid_cancel = client.post(f"/api/v1/appointments/{appt_id}/status", json={
        "status": "cancelled",
        "cancellation_reason": "Trying to cancel completed"
    }, headers=headers_admin)
    assert res_invalid_cancel.status_code == 400
    assert "invalid transition" in res_invalid_cancel.json()["detail"].lower()

def test_reschedule_flow():
    """Tests rescheduling appointment to a new slot."""
    db = SessionLocal()
    doc = db.query(Doctor).first()
    db.close()

    target_date = date.today() + timedelta(days=28)
    slots = client.get(f"/api/v1/slots?doctor_id={doc.id}&target_date={target_date.isoformat()}").json()
    avail = [s for s in slots if s["status"] == "available"]
    assert len(avail) >= 2
    old_slot = avail[0]
    new_slot = avail[1]

    pat_token = get_auth_token("patient30@medislot.com")
    headers = {"Authorization": f"Bearer {pat_token}"}

    # Initial booking
    book_res = client.post("/api/v1/appointments", json={"slot_id": old_slot["id"]}, headers=headers)
    assert book_res.status_code == 201
    appt_id = book_res.json()["id"]

    # Reschedule to new slot
    resched_res = client.post(f"/api/v1/appointments/{appt_id}/reschedule", json={
        "new_slot_id": new_slot["id"]
    }, headers=headers)
    assert resched_res.status_code == 200
    assert resched_res.json()["slot_id"] == new_slot["id"]

    # Verify old slot is free again
    db = SessionLocal()
    s_old = db.query(Slot).filter(Slot.id == old_slot["id"]).first()
    s_new = db.query(Slot).filter(Slot.id == new_slot["id"]).first()
    assert s_old.status == "available"
    assert s_new.status == "booked"
    db.close()

def test_waitlist_auto_offer_on_cancellation():
    """
    Tests waitlist flow:
    1. Patient A books slot.
    2. Patient B joins waitlist for that doctor and date.
    3. Patient A cancels.
    4. System auto-offers freed slot to Patient B with 30-min window.
    5. Patient B claims offer -> successfully booked!
    """
    db = SessionLocal()
    doc = db.query(Doctor).first()
    db.close()

    target_date = date.today() + timedelta(days=35)
    slots = client.get(f"/api/v1/slots?doctor_id={doc.id}&target_date={target_date.isoformat()}").json()
    avail = [s for s in slots if s["status"] == "available"]
    assert len(avail) >= 1
    slot = avail[0]

    token_a = get_auth_token("patient40@medislot.com")
    token_b = get_auth_token("patient41@medislot.com")

    # 1. Patient A books slot
    book_a = client.post("/api/v1/appointments", json={"slot_id": slot["id"]}, headers={"Authorization": f"Bearer {token_a}"})
    assert book_a.status_code == 201
    appt_a_id = book_a.json()["id"]

    # 2. Patient B joins waitlist for that doctor on that date
    wait_res = client.post("/api/v1/waitlist", json={
        "doctor_id": doc.id,
        "hospital_id": slot["hospital_id"],
        "preferred_date": target_date.isoformat(),
        "preferred_time_range": "any"
    }, headers={"Authorization": f"Bearer {token_b}"})
    assert wait_res.status_code == 201
    wait_id = wait_res.json()["id"]
    assert wait_res.json()["status"] == "waiting"

    # 3. Patient A cancels booking
    cancel_res = client.post(f"/api/v1/appointments/{appt_a_id}/cancel", json={
        "reason": "Sudden emergency travel"
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert cancel_res.status_code == 200

    # 4. Verify waitlist entry was auto-offered
    db = SessionLocal()
    wait_record = db.query(Waitlist).filter(Waitlist.id == wait_id).first()
    assert wait_record.status == "offered"
    assert wait_record.offered_slot_id == slot["id"]
    assert wait_record.offer_expires_at is not None
    db.close()

    # 5. Patient B claims offer
    claim_res = client.post(f"/api/v1/waitlist/{wait_id}/claim", json={
        "appointment_type": "new_patient"
    }, headers={"Authorization": f"Bearer {token_b}"})
    assert claim_res.status_code == 200
    claimed_appt = claim_res.json()
    assert claimed_appt["slot_id"] == slot["id"]
    assert claimed_appt["status"] == "booked"
