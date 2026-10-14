import pytest
import sys
import os
from fastapi.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.core.database import SessionLocal
from app.models.audit import AIInteractionLog
from app.services.triage import check_red_flags, EMERGENCY_HELPLINES, EMERGENCY_INSTRUCTIONS

client = TestClient(app)

# ---------------------------------------------------------------------------
# Test 1: Deterministic Red-Flag Triage - 100% Recall on Life Threats
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("emergency_phrase,expected_category", [
    ("I have crushing chest pain radiating to my left arm with severe cold sweats", "cardiac"),
    ("My father has sudden face drooping and slurred speech", "cerebrovascular"),
    ("Patient is gasping for air and turning blue unable to breathe", "respiratory_failure"),
    ("Woke up coughing up blood and feeling weak", "hemorrhage"),
    ("Severe allergic reaction after bee sting, throat closing cannot breathe", "anaphylaxis"),
    ("Friend is unresponsive and unconscious on the floor", "neurological_altered_mental"),
    ("Feeling suicidal and want to end my life", "psychiatric_crisis"),
])
def test_red_flag_emergency_recall(emergency_phrase, expected_category):
    is_emergency, conditions, category = check_red_flags(emergency_phrase)
    assert is_emergency is True, f"Failed to catch emergency phrase: {emergency_phrase}"
    assert category == expected_category
    assert len(conditions) > 0


# ---------------------------------------------------------------------------
# Test 2: Red-Flag API Endpoint Blocks Booking Prompts
# ---------------------------------------------------------------------------
def test_triage_api_emergency_blocking():
    payload = {
        "symptoms": "Severe crushing chest pain and heart attack symptoms for past 30 mins",
        "patient_age": 55,
        "patient_gender": "male",
    }
    response = client.post("/api/v1/ai/triage", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["red_flag_triggered"] is True
    assert data["urgency_level"] == "emergency"
    assert data["primary_specialty"] is None
    assert "108" in data["emergency_instructions"]
    assert any("108" in h for h in data["emergency_helplines"])
    assert any("112" in h for h in data["emergency_helplines"])


# ---------------------------------------------------------------------------
# Test 3: Routine Non-Emergency Symptom Specialty Mapping
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("symptoms,expected_spec", [
    ("Red itchy rash and pimples on both cheeks for 4 days", "Dermatology"),
    ("Sharp pain in right knee joint after twisting it while playing badminton", "Orthopedics"),
    ("Constant acidity and burning sensation in upper stomach after meals", "Gastroenterology"),
    ("Severe earache with blocked sensation and buzzing tinnitus sound", "ENT"),
    ("High blood pressure checkup and occasional palpitations", "Cardiology"),
    ("Mild fever and cough for 2 days with runny nose in my 5 year old kid", "Pediatrics"),
])
def test_triage_api_routine_specialty_mapping(symptoms, expected_spec):
    payload = {
        "symptoms": symptoms,
        "patient_age": 30 if "kid" not in symptoms else 5,
        "patient_gender": "female",
    }
    response = client.post("/api/v1/ai/triage", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["red_flag_triggered"] is False
    assert data["urgency_level"] in ["routine", "soon"]
    assert data["primary_specialty"] == expected_spec
    assert len(data["clinical_reasoning"]) > 10
    assert len(data["clarifying_questions"]) >= 1


# ---------------------------------------------------------------------------
# Test 4: Natural Language Doctor Search Query Parsing & Match
# ---------------------------------------------------------------------------
def test_parse_natural_language_search():
    payload = {
        "query": "female dermatologist in Coimbatore under 800 rupees speaking Tamil",
        "current_city": "Coimbatore"
    }
    response = client.post("/api/v1/ai/parse-search", json=payload)
    assert response.status_code == 200
    data = response.json()

    filters = data["filters"]
    assert filters["specialty"] == "Dermatology"
    assert filters["city"] == "Coimbatore"
    assert filters["gender"] == "female"
    assert filters["language"] == "Tamil"
    assert filters["max_fee"] == 800.0
    assert data["matched_doctors_count"] >= 1
    assert len(data["top_doctor_ids"]) >= 1


# ---------------------------------------------------------------------------
# Test 5: Conversational Assistant - Emergency Red-Flag Interception
# ---------------------------------------------------------------------------
def test_chat_assistant_emergency_interception():
    payload = {
        "messages": [
            {"role": "user", "content": "I have crushing chest pain and cold sweating, can I book a slot?"}
        ]
    }
    response = client.post("/api/v1/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["red_flag_triggered"] is True
    assert data["urgency_level"] == "emergency"
    assert data["suggested_action"] == "emergency"
    assert data["booking_proposal"] is None
    assert "108" in data["message"]


# ---------------------------------------------------------------------------
# Test 6: Conversational Assistant - Safe Human-in-the-Loop Proposal
# ---------------------------------------------------------------------------
def test_chat_assistant_safe_booking_proposal():
    db = SessionLocal()
    initial_log_count = db.query(AIInteractionLog).count()
    db.close()

    payload = {
        "messages": [
            {"role": "user", "content": "I twisted my ankle playing football and have severe knee and bone pain in Coimbatore"}
        ]
    }
    response = client.post("/api/v1/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["red_flag_triggered"] is False
    assert data["specialty_recommendation"] == "Orthopedics"
    if data["booking_proposal"]:
        proposal = data["booking_proposal"]
        assert proposal["doctor_id"] is not None
        assert proposal["slot_id"] is not None
        assert proposal["specialty"] == "Orthopedics"
        assert proposal["consultation_fee"] > 0
        assert data["suggested_action"] == "book_slot"

    # Verify audit log was created
    db = SessionLocal()
    new_log_count = db.query(AIInteractionLog).count()
    db.close()
    assert new_log_count > initial_log_count


# ---------------------------------------------------------------------------
# Test 7: AI Quota & Service Health Endpoint
# ---------------------------------------------------------------------------
def test_ai_quota_status():
    response = client.get("/api/v1/ai/quota")
    assert response.status_code == 200
    data = response.json()

    assert "gemini_configured" in data
    assert "model_name" in data
    assert "total_calls_today" in data
    assert data["daily_limit"] >= 1000
    assert data["status"] in ["active", "unconfigured", "daily_quota_exceeded"]
