import pytest
import sys
import os
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.core.database import SessionLocal
from app.models.appointment import Appointment
from app.models.schedule import Slot
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.services.ml_service import ml_service, MODEL_DIR, NO_SHOW_MODEL_FILE, WAIT_TIME_MODEL_FILE
from app.services.reminder import check_high_risk_no_show

client = TestClient(app)

# ---------------------------------------------------------------------------
# Test 1: Model Artifacts Integrity & Metadata
# ---------------------------------------------------------------------------

def test_ml_model_artifacts_exist_and_metadata_valid():
    """Validates that trained model binaries and evaluation metric files exist and are well-formed."""
    assert os.path.exists(NO_SHOW_MODEL_FILE), "No-show model file missing"
    assert os.path.exists(WAIT_TIME_MODEL_FILE), "Wait-time model file missing"

    info_res = client.get("/api/v1/ml/model-info")
    assert info_res.status_code == 200
    data = info_res.json()

    assert data["status"] == "healthy"
    assert "metrics" in data["no_show_model"]
    assert "roc_auc" in data["no_show_model"]["metrics"]
    assert data["no_show_model"]["metrics"]["roc_auc"] >= 0.65

    assert "metrics" in data["wait_time_model"]
    assert "mae_minutes" in data["wait_time_model"]["metrics"]
    assert data["wait_time_model"]["metrics"]["mae_minutes"] <= 4.0
    assert data["wait_time_model"]["metrics"]["mae_improvement_percent"] >= 20.0

# ---------------------------------------------------------------------------
# Test 2: Inference Latency Benchmark (< 20ms)
# ---------------------------------------------------------------------------

def test_ml_service_inference_latency():
    """Ensures inference pipeline is optimized and delivers predictions in under 20ms per call."""
    assert ml_service.is_ready is True

    payload = {
        "lead_time_days": 4.0,
        "appointment_type": "new_patient",
        "day_of_week": 2,
        "hour_of_day": 10.5,
        "patient_age": 45.0,
        "patient_gender": "Female",
        "past_appointments": 2,
        "past_no_shows": 0,
        "doctor_specialty": "Cardiology",
        "doctor_experience_years": 14,
        "consultation_fee": 700.0
    }

    # Warmup
    client.post("/api/v1/ml/predict-no-show", json=payload)

    # Benchmark 50 calls
    start_t = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        res = client.post("/api/v1/ml/predict-no-show", json=payload)
        assert res.status_code == 200
    elapsed_ms = ((time.perf_counter() - start_t) / iterations) * 1000.0

    print(f"\nAverage ML inference latency: {elapsed_ms:.2f} ms")
    assert elapsed_ms < 20.0, f"Inference latency too high: {elapsed_ms:.2f} ms (target < 20ms)"

# ---------------------------------------------------------------------------
# Test 3: Speculative No-Show Risk Stratification
# ---------------------------------------------------------------------------

def test_predict_no_show_risk_stratification():
    """
    Validates calibrated sensitivity:
    - Short lead time + clean record -> Low risk.
    - Long lead time (18 days) + repeat past no-shows + new patient -> High risk.
    """
    # Low risk scenario
    low_res = client.post("/api/v1/ml/predict-no-show", json={
        "lead_time_days": 1.0,
        "appointment_type": "follow_up",
        "day_of_week": 1,
        "hour_of_day": 10.0,
        "patient_age": 52.0,
        "past_appointments": 5,
        "past_no_shows": 0,
        "doctor_specialty": "General Medicine"
    })
    assert low_res.status_code == 200
    low_data = low_res.json()
    assert low_data["no_show_probability"] < 0.35
    assert low_data["is_high_risk"] is False

    # High risk scenario
    high_res = client.post("/api/v1/ml/predict-no-show", json={
        "lead_time_days": 18.0,
        "appointment_type": "new_patient",
        "day_of_week": 4,
        "hour_of_day": 12.5,
        "patient_age": 24.0,
        "past_appointments": 4,
        "past_no_shows": 3,
        "doctor_specialty": "Dermatology"
    })
    assert high_res.status_code == 200
    high_data = high_res.json()
    assert high_data["no_show_probability"] > low_data["no_show_probability"]
    assert high_data["is_high_risk"] is True
    assert high_data["risk_level"] == "high"
    assert len(high_data["top_risk_factors"]) > 0

# ---------------------------------------------------------------------------
# Test 4: Dynamic Prediction for Real Database Appointment
# ---------------------------------------------------------------------------

def test_predict_no_show_for_database_appointment():
    """Validates that ML model dynamically extracts features directly from an existing appointment ID."""
    db = SessionLocal()
    appt = db.query(Appointment).first()
    assert appt is not None
    appt_id = str(appt.id)
    db.close()

    res = client.post("/api/v1/ml/predict-no-show", json={"appointment_id": appt_id})
    assert res.status_code == 200
    data = res.json()

    assert 0.0 <= data["no_show_probability"] <= 1.0
    assert data["risk_level"] in ["low", "medium", "high"]
    assert len(data["recommended_action"]) > 0
    assert isinstance(data["top_risk_factors"], list)

# ---------------------------------------------------------------------------
# Test 5: Consultation Duration Regression
# ---------------------------------------------------------------------------

def test_predict_consultation_duration():
    """
    Validates duration regression:
    - New patient consultation takes longer than brief follow-up.
    - Complex specialty (Cardiology) takes longer than routine (Dermatology).
    - Predictions are strictly bounded within clinical operating limits (8 to 50 mins).
    """
    # Cardiology new patient
    res_cardio = client.post("/api/v1/ml/predict-duration", json={
        "appointment_type": "new_patient",
        "doctor_specialty": "Cardiology",
        "day_of_week": 1,
        "hour_of_day": 10.0,
        "patient_age": 55.0,
        "doctor_experience_years": 8,
        "estimated_duration_minutes": 25
    })
    assert res_cardio.status_code == 200
    cardio_data = res_cardio.json()

    # Dermatology follow-up
    res_derma = client.post("/api/v1/ml/predict-duration", json={
        "appointment_type": "follow_up",
        "doctor_specialty": "Dermatology",
        "day_of_week": 3,
        "hour_of_day": 11.0,
        "patient_age": 30.0,
        "doctor_experience_years": 18,
        "estimated_duration_minutes": 15
    })
    assert res_derma.status_code == 200
    derma_data = res_derma.json()

    assert cardio_data["predicted_duration_minutes"] > derma_data["predicted_duration_minutes"]
    assert 8.0 <= cardio_data["predicted_duration_minutes"] <= 50.0
    assert 8.0 <= derma_data["predicted_duration_minutes"] <= 50.0
    assert "clinical_load" in cardio_data

# ---------------------------------------------------------------------------
# Test 6: Integration with Reminder Service Check Hook
# ---------------------------------------------------------------------------

def test_reminder_service_integrates_ml_model():
    """Validates that check_high_risk_no_show executes ML model inference seamlessly."""
    db = SessionLocal()
    doc = db.query(Doctor).first()
    pat = db.query(Patient).first()

    # Create dummy slot and appointment
    slot = Slot(
        doctor_id=doc.id,
        hospital_id=doc.hospitals[0].hospital_id,
        slot_start=datetime.now(timezone.utc) + timedelta(days=2),
        slot_end=datetime.now(timezone.utc) + timedelta(days=2, minutes=20)
    )
    appt = Appointment(patient_id=pat.id, slot=slot, appointment_type="follow_up")

    # Calling check_high_risk_no_show should invoke ML inference and return a bool without exception
    result = check_high_risk_no_show(appt, db)
    assert isinstance(result, bool)
    db.close()
