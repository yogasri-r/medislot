import pytest
import sys
import os
from fastapi.testclient import TestClient

# Ensure backend root is on path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.core.security import verify_password, hash_password
from app.core.database import SessionLocal
from app.models.hospital import Hospital
from app.models.user import User

client = TestClient(app)

def test_password_hashing_argon2():
    password = "SecurePassword@2026"
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_patient_registration_and_login():
    import uuid, random
    uid = uuid.uuid4().hex[:8]
    random_phone = f"+919{random.randint(100000000, 999999999)}"
    reg_payload = {
        "email": f"test.patient.{uid}@medislot.com",
        "password": "PatientPassword@123",
        "full_name": "Test Patient",
        "phone": random_phone,
        "role": "patient",
        "date_of_birth": "1995-05-15",
        "gender": "female",
        "blood_group": "O+",
        "preferred_language": "Tamil"
    }
    
    # 1. Register
    response = client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == reg_payload["email"]
    assert data["user"]["role"] == "patient"
    
    # 2. Duplicate registration rejected
    dup_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 400
    
    # 3. Login with valid credentials
    login_res = client.post("/api/v1/auth/login", json={
        "email": reg_payload["email"],
        "password": "PatientPassword@123"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    token = login_data["access_token"]
    
    # 4. Verify /auth/me with bearer token
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == reg_payload["email"]
    
    # 5. Login with invalid password rejected
    bad_login = client.post("/api/v1/auth/login", json={
        "email": reg_payload["email"],
        "password": "IncorrectPassword"
    })
    assert bad_login.status_code == 401

def test_cannot_register_super_admin_publicly():
    payload = {
        "email": "hacker.admin@medislot.com",
        "password": "HackedPassword@123",
        "full_name": "Fake Admin",
        "phone": "+919999900099",
        "role": "super_admin"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 403

def test_refresh_token_flow():
    # Login as seeded patient
    res = client.post("/api/v1/auth/login", json={
        "email": "patient1@medislot.com",
        "password": "Patient@123456"
    })
    assert res.status_code == 200
    refresh_token = res.json()["refresh_token"]
    
    # Refresh
    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    ref_data = refresh_res.json()
    assert "access_token" in ref_data
    assert "refresh_token" in ref_data

def test_hospital_scoped_rbac_isolation():
    """
    CRITICAL TEST:
    A hospital_admin must NEVER be able to read or modify another hospital's data.
    """
    db = SessionLocal()
    admin_user = db.query(User).filter(User.email == "admin.coimbatore@medislot.com").first()
    assert admin_user is not None
    own_hosp = db.query(Hospital).filter(Hospital.id == admin_user.hospital_id).first()
    other_hosp = db.query(Hospital).filter(Hospital.id != admin_user.hospital_id).first()
    assert own_hosp is not None
    assert other_hosp is not None
    db.close()

    # Login as Coimbatore Hospital Admin
    admin1_res = client.post("/api/v1/auth/login", json={
        "email": "admin.coimbatore@medislot.com",
        "password": "Hospital@123456"
    })
    assert admin1_res.status_code == 200
    token1 = admin1_res.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Attempt 1: Coimbatore Hospital Admin updates their own hospital (SHOULD SUCCEED)
    res_allowed = client.put(f"/api/v1/hospitals/{own_hosp.id}", json={
        "address": "Updated Address By Own Admin"
    }, headers=headers1)
    assert res_allowed.status_code == 200, res_allowed.text
    assert res_allowed.json()["address"] == "Updated Address By Own Admin"

    # Attempt 2: Coimbatore Hospital Admin tries to update another hospital (MUST BE FORBIDDEN 403)
    res_forbidden = client.put(f"/api/v1/hospitals/{other_hosp.id}", json={
        "address": "Malicious Tampering By Alien Admin"
    }, headers=headers1)
    assert res_forbidden.status_code == 403
    assert "another hospital" in res_forbidden.json()["detail"].lower()

def test_patient_forbidden_from_admin_actions():
    # Login as regular patient
    pat_res = client.post("/api/v1/auth/login", json={
        "email": "patient1@medislot.com",
        "password": "Patient@123456"
    })
    token = pat_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to create a hospital (requires super_admin)
    create_hosp = client.post("/api/v1/hospitals", json={
        "name": "Unauthorized Hospital",
        "slug": "unauthorized-hosp",
        "address": "Nowhere",
        "city": "Unknown",
        "postal_code": "000000",
        "phone": "+910000000000",
        "email": "bad@hospital.com"
    }, headers=headers)
    assert create_hosp.status_code == 403

def test_super_admin_global_access():
    admin_res = client.post("/api/v1/auth/login", json={
        "email": "admin@medislot.com",
        "password": "Admin@123456"
    })
    assert admin_res.status_code == 200
    token = admin_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Super admin can list and verify doctors
    docs_res = client.get("/api/v1/doctors?verified_only=false", headers=headers)
    assert docs_res.status_code == 200
    doctors = docs_res.json()
    assert len(doctors) >= 40

def test_doctor_search_filters():
    # 1. Search by specialty
    cardio_res = client.get("/api/v1/doctors?specialty=Cardiology")
    assert cardio_res.status_code == 200
    cardio_docs = cardio_res.json()
    assert len(cardio_docs) >= 1
    for d in cardio_docs:
        assert "cardiology" in d["specialty"].lower()

    # 2. Search by city
    coimbatore_res = client.get("/api/v1/doctors?city=Coimbatore")
    assert coimbatore_res.status_code == 200
    cbe_docs = coimbatore_res.json()
    assert len(cbe_docs) >= 1

    # 3. Search by language
    hindi_res = client.get("/api/v1/doctors?language=Hindi")
    assert hindi_res.status_code == 200
    hindi_docs = hindi_res.json()
    for d in hindi_docs:
        assert any("hindi" in l.lower() for l in d["languages_spoken"])

def test_hospital_dashboard_stats_and_tenancy():
    db = SessionLocal()
    hosp1 = db.query(Hospital).filter(Hospital.city == "Coimbatore").first()
    hosp2 = db.query(Hospital).filter(Hospital.city != "Coimbatore").first()
    db.close()

    # Login as Coimbatore Hospital Admin
    admin_res = client.post("/api/v1/auth/login", json={
        "email": "admin.coimbatore@medislot.com",
        "password": "Hospital@123456"
    })
    token = admin_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Allowed: access own hospital stats
    res_allowed = client.get(f"/api/v1/hospitals/{hosp1.id}/dashboard-stats", headers=headers)
    assert res_allowed.status_code == 200
    data = res_allowed.json()
    assert "stats" in data
    assert "departments" in data
    assert "doctors" in data
    assert data["stats"]["total_doctors"] >= 1

    # Forbidden: access other hospital stats (403)
    res_forbidden = client.get(f"/api/v1/hospitals/{hosp2.id}/dashboard-stats", headers=headers)
    assert res_forbidden.status_code == 403

def test_super_admin_network_analytics():
    # Super admin login
    admin_res = client.post("/api/v1/auth/login", json={
        "email": "admin@medislot.com",
        "password": "Admin@123456"
    })
    token = admin_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/hospitals/network-analytics", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "network_stats" in data
    assert data["network_stats"]["total_hospitals"] >= 4
    assert data["network_stats"]["total_doctors"] >= 40
    assert len(data["hospitals"]) >= 4

    # Hospital admin forbidden from global network analytics (403)
    hosp_res = client.post("/api/v1/auth/login", json={
        "email": "admin.coimbatore@medislot.com",
        "password": "Hospital@123456"
    })
    hosp_token = hosp_res.json()["access_token"]
    hosp_headers = {"Authorization": f"Bearer {hosp_token}"}
    res_denied = client.get("/api/v1/hospitals/network-analytics", headers=hosp_headers)
    assert res_denied.status_code == 403
