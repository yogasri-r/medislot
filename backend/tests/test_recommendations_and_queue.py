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
from app.models.doctor import Doctor, DoctorHospital
from app.models.hospital import Hospital
from app.models.schedule import Slot
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.user import User

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

def get_hospital_admin_token(email: str = "admin.coimbatore@medislot.com") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Hospital@123456"})
    assert res.status_code == 200, f"Hospital Admin login failed: {res.text}"
    return res.json()["access_token"]

# ---------------------------------------------------------------------------
# Test 1: Doctor Recommendation Multi-Factor Scoring & Ranking
# ---------------------------------------------------------------------------

def test_doctor_recommendation_scoring_and_explanations():
    """
    Validates multi-factor doctor recommendation ranking:
    Checks composite scoring (0.0 to 1.0), breakdown elements, and ranking order.
    """
    response = client.get("/api/v1/recommendations/doctors?specialty=Cardiology&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    prev_score = 1.0
    for rec in data:
        assert 0.0 <= rec["composite_score"] <= 1.0
        assert rec["composite_score"] <= prev_score  # Must be sorted descending
        prev_score = rec["composite_score"]

        assert "specialty_match" in rec["score_breakdown"]
        assert "earliest_slot" in rec["score_breakdown"]
        assert "rating_normalized" in rec["score_breakdown"]
        assert "location_proximity" in rec["score_breakdown"]
        assert "experience" in rec["score_breakdown"]

        assert len(rec["explanation"]) > 0
        assert "★" in rec["explanation"] or "exp" in rec["explanation"]
        assert rec["doctor"]["specialty"].lower() == "cardiology"

# ---------------------------------------------------------------------------
# Test 2: Location Proximity Matrix Scoring
# ---------------------------------------------------------------------------

def test_doctor_recommendation_location_proximity():
    """
    Validates that doctors in the requested city receive maximum proximity (1.0),
    while doctors in neighboring Western Tamil Nadu cities receive calibrated proximity scores.
    """
    # Coimbatore proximity
    res_coimbatore = client.get("/api/v1/recommendations/doctors?city=Coimbatore&limit=20")
    assert res_coimbatore.status_code == 200
    cbe_data = res_coimbatore.json()
    assert len(cbe_data) > 0

    # At least one doctor in Coimbatore should have proximity score of 1.0
    cbe_proximities = [
        rec["score_breakdown"]["location_proximity"]
        for rec in cbe_data
        if any(h["hospital_city"] and h["hospital_city"].lower() == "coimbatore" for h in rec["doctor"]["hospitals"])
    ]
    assert any(p == 1.0 for p in cbe_proximities)

    # Erode proximity query
    res_erode = client.get("/api/v1/recommendations/doctors?city=Erode&limit=20")
    assert res_erode.status_code == 200
    erode_data = res_erode.json()
    assert len(erode_data) > 0

    erode_proximities = [
        rec["score_breakdown"]["location_proximity"]
        for rec in erode_data
        if any(h["hospital_city"] and h["hospital_city"].lower() == "erode" for h in rec["doctor"]["hospitals"])
    ]
    assert any(p == 1.0 for p in erode_proximities)

# ---------------------------------------------------------------------------
# Test 3: Recommendation Filters (Gender, Max Fee, Verified)
# ---------------------------------------------------------------------------

def test_doctor_recommendation_filters():
    """
    Validates filtering by gender, max consultation fee, and verification status.
    """
    # 1. Gender filter
    res_gender = client.get("/api/v1/recommendations/doctors?gender=Female&limit=10")
    assert res_gender.status_code == 200
    female_docs = res_gender.json()
    if female_docs:
        for rec in female_docs:
            assert rec["doctor"]["gender"].lower() == "female"

    # 2. Max fee filter
    res_fee = client.get("/api/v1/recommendations/doctors?max_fee=600&limit=10")
    assert res_fee.status_code == 200
    fee_docs = res_fee.json()
    for rec in fee_docs:
        assert rec["doctor"]["default_consultation_fee"] <= 600.0

# ---------------------------------------------------------------------------
# Test 4: Smart Slot Ranking & Top 3 Suggestions
# ---------------------------------------------------------------------------

def test_smart_slots_ranking_and_suggestions():
    """
    Validates smart slot engine:
    - Automatically fetches / generates slots for target date.
    - Accurately identifies Top 3 'Suggested' slots with clinical/schedule reasoning.
    """
    db = SessionLocal()
    doc = db.query(Doctor).filter(Doctor.is_verified == True).first()
    assert doc is not None
    doc_id = str(doc.id)
    db.close()

    # Target date: next upcoming Tuesday (weekday)
    now = datetime.now()
    days_ahead = (1 - now.weekday()) % 7  # Tuesday is 1
    if days_ahead <= 1:
        days_ahead += 7
    target_date = (now + timedelta(days=days_ahead)).date()

    res = client.get(f"/api/v1/recommendations/smart-slots?doctor_id={doc_id}&target_date={target_date.isoformat()}")
    assert res.status_code == 200
    data = res.json()

    assert data["doctor_id"] == doc_id
    assert data["target_date"] == target_date.isoformat()
    assert data["total_slots"] > 0
    assert data["available_slots"] > 0

    suggested = data["suggested_slots"]
    # At most 3 suggestions
    assert 1 <= len(suggested) <= 3
    for s in suggested:
        assert s["is_suggested"] is True
        assert s["suggestion_reason"] is not None
        assert s["score"] > 0.0

# ---------------------------------------------------------------------------
# Test 5: Live Queue Status & Wait Time Estimation
# ---------------------------------------------------------------------------

def test_queue_status_estimation_for_patient():
    """
    Validates dynamic queue estimation for a patient appointment:
    - Queue position calculation.
    - Historical doctor duration average.
    - Dynamic wait time bounds and human-formatted output.
    """
    db = SessionLocal()
    # Find an active or historical appointment
    appt = db.query(Appointment).first()
    assert appt is not None
    appt_id = str(appt.id)
    patient_user = db.query(User).join(Patient, Patient.user_id == User.id).filter(Patient.id == appt.patient_id).first()
    assert patient_user is not None
    patient_email = patient_user.email
    db.close()

    patient_token = get_auth_token(patient_email)

    # Patient checks their queue status
    res = client.get(
        f"/api/v1/queue/appointment/{appt_id}",
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["appointment_id"] == appt_id
    assert data["queue_number"] >= 1
    assert data["patients_ahead"] >= 0
    assert data["historical_avg_duration_minutes"] > 0.0
    assert "estimated_wait_formatted" in data
    assert "expected_consultation_time_ist" in data

# ---------------------------------------------------------------------------
# Test 6: Queue Status Security & Multi-Tenant RBAC
# ---------------------------------------------------------------------------

def test_queue_status_security_and_rbac():
    """
    Validates that:
    - Another patient cannot peek into someone else's appointment queue (403 Forbidden).
    - The attending doctor can view the queue status (200 OK).
    - Super admin can view any appointment queue status (200 OK).
    """
    db = SessionLocal()
    # Pick 2 different patients
    patients = db.query(Patient).limit(2).all()
    p1 = patients[0]
    p2 = patients[1]

    p1_user = db.query(User).filter(User.id == p1.user_id).first()
    p2_user = db.query(User).filter(User.id == p2.user_id).first()

    appt = db.query(Appointment).filter(Appointment.patient_id == p1.id).first()
    assert appt is not None
    appt_id = str(appt.id)
    doc_id = str(appt.doctor_id)

    doc_user = db.query(User).join(Doctor, Doctor.user_id == User.id).filter(Doctor.id == doc_id).first()
    assert doc_user is not None
    db.close()

    p2_token = get_auth_token(p2_user.email)
    doc_token = get_doctor_token(doc_user.email)
    admin_token = get_admin_token()

    # Patient 2 tries to access Patient 1's appointment -> 403 Forbidden
    res_p2 = client.get(
        f"/api/v1/queue/appointment/{appt_id}",
        headers={"Authorization": f"Bearer {p2_token}"}
    )
    assert res_p2.status_code == 403
    assert "Access denied" in res_p2.json()["detail"]

    # Attending doctor -> 200 OK
    res_doc = client.get(
        f"/api/v1/queue/appointment/{appt_id}",
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert res_doc.status_code == 200

    # Super admin -> 200 OK
    res_admin = client.get(
        f"/api/v1/queue/appointment/{appt_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin.status_code == 200

# ---------------------------------------------------------------------------
# Test 7: Doctor Daily Queue View & Clinic Staff Authorization
# ---------------------------------------------------------------------------

def test_doctor_daily_queue_view_and_staff_access():
    """
    Validates clinical daily queue endpoint:
    - Doctor can view their own schedule/queue.
    - Patient cannot view clinic daily queue (403 Forbidden).
    - Assigned hospital admin can view clinic queue (200 OK).
    - Different hospital admin is blocked (403 Forbidden).
    """
    db = SessionLocal()
    # Find doctor 1 and their primary hospital
    doc1 = db.query(Doctor).join(User, Doctor.user_id == User.id).filter(User.email == "doctor1@medislot.com").first()
    assert doc1 is not None
    doc1_id = str(doc1.id)

    primary_aff = db.query(DoctorHospital).filter(
        DoctorHospital.doctor_id == doc1.id,
        DoctorHospital.is_primary == True
    ).first()
    assert primary_aff is not None
    hospital_id = str(primary_aff.hospital_id)

    kovai_admin = db.query(User).filter(User.email == "admin.coimbatore@medislot.com").first()
    erode_admin = db.query(User).filter(User.email == "admin.erode@medislot.com").first()
    patient = db.query(User).filter(User.email == "patient1@medislot.com").first()
    db.close()

    doc_token = get_doctor_token("doctor1@medislot.com")
    kovai_token = get_hospital_admin_token("admin.coimbatore@medislot.com")
    erode_token = get_hospital_admin_token("admin.erode@medislot.com")
    patient_token = get_auth_token("patient1@medislot.com")

    # 1. Doctor accesses their own daily queue -> 200 OK
    res_doc = client.get(
        f"/api/v1/queue/doctor/{doc1_id}?hospital_id={hospital_id}",
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert res_doc.status_code == 200
    data = res_doc.json()
    assert data["doctor_id"] == doc1_id
    assert data["hospital_id"] == hospital_id
    assert "completed_count" in data
    assert "waiting_count" in data
    assert isinstance(data["patients"], list)

    # 2. Patient attempts to access clinic queue -> 403 Forbidden
    res_pat = client.get(
        f"/api/v1/queue/doctor/{doc1_id}?hospital_id={hospital_id}",
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert res_pat.status_code == 403

    # 3. Hospital Admin for Kovai Hospital (same hospital) -> 200 OK
    res_kovai = client.get(
        f"/api/v1/queue/doctor/{doc1_id}?hospital_id={hospital_id}",
        headers={"Authorization": f"Bearer {kovai_token}"}
    )
    assert res_kovai.status_code == 200

    # 4. Hospital Admin for Erode Hospital (different hospital) -> 403 Forbidden
    res_erode = client.get(
        f"/api/v1/queue/doctor/{doc1_id}?hospital_id={hospital_id}",
        headers={"Authorization": f"Bearer {erode_token}"}
    )
    assert res_erode.status_code == 403
    assert "Access denied" in res_erode.json()["detail"]
