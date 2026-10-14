import json
import logging
import re
import time
from datetime import datetime, timezone, timedelta, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import AIInteractionLog
from app.models.doctor import Doctor, DoctorHospital
from app.models.hospital import Hospital
from app.models.appointment import Appointment
from app.models.schedule import Slot
from app.services.triage import (
    check_red_flags,
    EMERGENCY_HELPLINES,
    EMERGENCY_INSTRUCTIONS,
)
from app.services.llm_client import gemini_client
from app.services.recommendation import recommend_doctors
from app.services.smart_slots import rank_slots_for_doctor
from app.services.availability import convert_utc_to_ist_str, IST_ZONE
from app.schemas.ai import (
    TriageRequest,
    TriageResponse,
    NLSearchRequest,
    NLSearchFilterResult,
    NLSearchResponse,
    AIChatRequest,
    AIChatResponse,
    BookingProposal,
    AIQuotaStatus,
)

logger = logging.getLogger(__name__)

VALID_SPECIALTIES = [
    "Cardiology",
    "Dermatology",
    "ENT",
    "Gastroenterology",
    "General Medicine",
    "Gynecology",
    "Neurology",
    "Ophthalmology",
    "Orthopedics",
    "Pediatrics",
]

SPECIALTY_KEYWORDS = {
    "Cardiology": [
        "heart", "cardio", "cardiologist", "cardiology", "chest discomfort", "palpitation", "high bp", "hypertension",
        "blood pressure", "heartbeat", "cholesterol", "ecg"
    ],
    "Dermatology": [
        "skin", "dermatologist", "dermatology", "rash", "acne", "pimple", "itching", "eczema", "hair fall", "dandruff",
        "psoriasis", "mole", "fungal", "pigmentation", "allergy on skin"
    ],
    "ENT": [
        "ear", "nose", "throat", "ent", "ent specialist", "sinus", "tonsil", "hearing", "earache", "nasal",
        "hoarseness", "vertigo", "tinnitus", "loss of smell"
    ],
    "Gastroenterology": [
        "stomach", "gastro", "gastroenterologist", "gastroenterology", "gastric", "acidity", "indigestion", "bloating", "abdomen", "liver",
        "diarrhea", "constipation", "ulcer", "vomiting", "gerd", "reflux", "jaundice"
    ],
    "General Medicine": [
        "physician", "general physician", "general doctor", "fever", "cold", "cough", "flu", "body pain", "fatigue", "weakness", "infection",
        "general checkup", "malaise", "head cold", "chills"
    ],
    "Gynecology": [
        "gynecologist", "gynecology", "gynec", "obgyn", "period", "menstrual", "pregnancy", "pelvic", "fertility", "ovary", "pcos",
        "uterus", "cramps", "antenatal"
    ],
    "Neurology": [
        "neurologist", "neurology", "neuro", "headache", "migraine", "dizziness", "nerve", "tremor", "numbness", "tingling",
        "memory loss", "seizure", "brain", "sciatica"
    ],
    "Ophthalmology": [
        "ophthalmologist", "ophthalmology", "eye doctor", "eye", "vision", "blur", "glasses", "cataract", "redness in eye", "itchy eyes",
        "watery eyes", "glaucoma", "sight"
    ],
    "Orthopedics": [
        "orthopedic", "orthopedics", "orthopedist", "ortho", "bone doctor", "bone", "joint", "knee", "back pain", "shoulder", "spine", "fracture",
        "sprain", "arthritis", "ligament", "neck pain", "swollen joint", "hip"
    ],
    "Pediatrics": [
        "pediatrician", "pediatrics", "pediatric", "child doctor", "child specialist", "child", "baby", "infant", "toddler", "kid", "vaccination",
        "growth", "newborn", "colic"
    ],
}

VALID_CITIES = ["Coimbatore", "Erode", "Tiruppur", "Dharapuram"]


def _log_interaction(
    db: Session,
    user_id: Optional[str],
    feature_type: str,
    input_text: str,
    red_flag: bool,
    urgency: Optional[str],
    entities: Optional[Dict[str, Any]],
    raw_response: Optional[Dict[str, Any]],
    latency_ms: int,
    status: str,
    tools_called: Optional[List[str]] = None,
):
    """Persists an audit record to ai_interaction_logs table."""
    try:
        # Anonymize/truncate text if necessary
        clean_text = (input_text or "").strip()[:500]
        log = AIInteractionLog(
            user_id=user_id,
            feature_type=feature_type,
            input_text_anonymized=clean_text,
            red_flag_triggered=red_flag,
            urgency_level=urgency,
            extracted_entities=entities,
            tools_called=tools_called or [],
            raw_response_json=raw_response,
            latency_ms=latency_ms,
            status=status,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to record AIInteractionLog: {e}")
        db.rollback()


def _deterministic_symptom_fallback(symptoms: str, age: Optional[int], gender: Optional[str]) -> Tuple[str, Optional[str], str, str, List[str]]:
    """
    Rule-based deterministic specialty matcher when LLM is unavailable.
    Returns (primary_specialty, secondary_specialty, urgency, reasoning, questions)
    """
    lower = symptoms.lower()

    # Pediatric age heuristic
    if age is not None and age <= 14:
        return (
            "Pediatrics",
            "General Medicine",
            "routine",
            "Patient age is 14 or under; pediatric evaluation is recommended for child healthcare.",
            ["How long has your child had these symptoms?", "Has there been any fever or change in feeding/appetite?"]
        )

    matched_scores: Dict[str, int] = {}
    for spec, keywords in SPECIALTY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score > 0:
            matched_scores[spec] = score

    if matched_scores:
        sorted_specs = sorted(matched_scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_specs[0][0]
        secondary = sorted_specs[1][0] if len(sorted_specs) > 1 else "General Medicine"
    else:
        primary = "General Medicine"
        secondary = None

    # Urgency heuristic
    soon_triggers = ["severe", "high fever", "unable to sleep", "worsening", "days", "intense", "sharp"]
    urgency = "soon" if any(t in lower for t in soon_triggers) else "routine"

    reasoning = f"Reported symptoms strongly align with clinical presentations evaluated in {primary}."
    questions = [
        "How many days have you been experiencing these symptoms?",
        "Are symptoms accompanied by any high fever or sudden changes?",
        "Have you taken any over-the-counter medications for this?"
    ]

    return primary, secondary, urgency, reasoning, questions


def triage_patient_symptoms(
    req: TriageRequest,
    db: Session,
    user_id: Optional[str] = None
) -> TriageResponse:
    """
    Two-step symptom triage:
    1. Deterministic Red-Flag check for life-threatening emergencies.
    2. LLM or rule-based specialty recommendation.
    """
    start_time = time.time()

    # Step 1: Immediate Red-Flag Check
    is_emergency, matched_patterns, category = check_red_flags(req.symptoms)

    if is_emergency:
        latency = int((time.time() - start_time) * 1000)
        _log_interaction(
            db=db,
            user_id=user_id,
            feature_type="symptom_triage",
            input_text=req.symptoms,
            red_flag=True,
            urgency="emergency",
            entities={"category": category, "matched_patterns": matched_patterns},
            raw_response={"status": "emergency_blocked", "conditions": matched_patterns},
            latency_ms=latency,
            status="emergency_blocked",
        )

        return TriageResponse(
            red_flag_triggered=True,
            urgency_level="emergency",
            primary_specialty=None,
            secondary_specialty=None,
            clinical_reasoning=f"Critical symptoms detected ({', '.join(matched_patterns)}). Emergency intervention required.",
            clarifying_questions=[],
            emergency_instructions=EMERGENCY_INSTRUCTIONS,
            emergency_helplines=EMERGENCY_HELPLINES,
            is_fallback=False,
        )

    # Step 2: Gemini LLM Specialty Mapping
    prompt = f"""
Patient reported symptoms: "{req.symptoms}"
Patient Age: {req.patient_age if req.patient_age is not None else 'Unknown'}
Patient Gender: {req.patient_gender if req.patient_gender else 'Unknown'}
Duration: {req.duration_days if req.duration_days is not None else 'Unknown'} days

Valid specialties: {json.dumps(VALID_SPECIALTIES)}

Return a JSON object with:
- "primary_specialty": Exactly one string from the valid specialties list.
- "secondary_specialty": Another valid specialty from the list, or null.
- "urgency_level": "routine" or "soon".
- "clinical_reasoning": Concise explanation (1-2 sentences) of why this specialty is appropriate.
- "clarifying_questions": A list of 2-3 relevant clinical questions a doctor would ask.
"""
    system_instruction = (
        "You are MediSlot's expert clinical triage advisor for Western Tamil Nadu outpatient hospitals. "
        "Recommend the most appropriate medical specialty. Adhere strictly to the provided list of valid specialties. "
        "Do not diagnose diseases; recommend the correct medical department."
    )

    llm_res = gemini_client.generate_json(prompt=prompt, system_instruction=system_instruction)
    is_fallback = False

    if (
        llm_res
        and isinstance(llm_res, dict)
        and llm_res.get("primary_specialty") in VALID_SPECIALTIES
    ):
        primary = llm_res["primary_specialty"]
        secondary = llm_res.get("secondary_specialty")
        if secondary not in VALID_SPECIALTIES:
            secondary = None
        urgency = llm_res.get("urgency_level", "routine")
        if urgency not in ["routine", "soon"]:
            urgency = "routine"
        reasoning = llm_res.get("clinical_reasoning", f"Symptoms correspond to the field of {primary}.")
        questions = llm_res.get("clarifying_questions", [])
        status_label = "success"
    else:
        # Fallback
        is_fallback = True
        primary, secondary, urgency, reasoning, questions = _deterministic_symptom_fallback(
            req.symptoms, req.patient_age, req.patient_gender
        )
        status_label = "fallback"

    latency = int((time.time() - start_time) * 1000)
    _log_interaction(
        db=db,
        user_id=user_id,
        feature_type="symptom_triage",
        input_text=req.symptoms,
        red_flag=False,
        urgency=urgency,
        entities={"primary_specialty": primary, "secondary_specialty": secondary},
        raw_response=llm_res,
        latency_ms=latency,
        status=status_label,
    )

    return TriageResponse(
        red_flag_triggered=False,
        urgency_level=urgency,
        primary_specialty=primary,
        secondary_specialty=secondary,
        clinical_reasoning=reasoning,
        clarifying_questions=questions,
        emergency_instructions=None,
        emergency_helplines=[],
        is_fallback=is_fallback,
    )


def _deterministic_extract_filters(query: str) -> NLSearchFilterResult:
    """Regex/keyword extraction for natural language doctor search queries."""
    lower = query.lower()

    # Specialty
    matched_spec = None
    for spec, kws in SPECIALTY_KEYWORDS.items():
        if spec.lower() in lower or any(kw in lower for kw in kws):
            matched_spec = spec
            break

    # City
    matched_city = None
    for city in VALID_CITIES:
        if city.lower() in lower:
            matched_city = city
            break

    # Gender
    matched_gender = None
    if re.search(r"\b(?:female|lady|woman)\b", lower):
        matched_gender = "female"
    elif re.search(r"\b(?:male|man)\b", lower):
        matched_gender = "male"

    # Language
    matched_lang = None
    for lang in ["Tamil", "English", "Hindi"]:
        if lang.lower() in lower:
            matched_lang = lang
            break

    # Max fee: e.g. "under 800", "below 1000", "500 rs", "< 600"
    matched_fee = None
    fee_match = re.search(r"(?:under|below|less than|max|up to|within)?\s*(?:rs\.?|inr|₹)?\s*(\d{3,4})\s*(?:rs|rupees|inr)?", lower)
    if fee_match:
        val = float(fee_match.group(1))
        if 200 <= val <= 3000:
            matched_fee = val

    # Date intent
    date_intent = None
    if "today" in lower:
        date_intent = "today"
    elif "tomorrow" in lower:
        date_intent = "tomorrow"
    elif "weekend" in lower or "saturday" in lower or "sunday" in lower:
        date_intent = "this_weekend"
    elif "next week" in lower:
        date_intent = "next_week"

    summary_parts = []
    if matched_spec:
        summary_parts.append(f"{matched_spec}")
    if matched_city:
        summary_parts.append(f"in {matched_city}")
    if matched_gender:
        summary_parts.append(f"({matched_gender})")
    if matched_fee:
        summary_parts.append(f"≤ ₹{int(matched_fee)}")
    if matched_lang:
        summary_parts.append(f"speaking {matched_lang}")
    if date_intent:
        summary_parts.append(f"for {date_intent.replace('_', ' ')}")

    summary = " • ".join(summary_parts) if summary_parts else "General doctor search"

    return NLSearchFilterResult(
        specialty=matched_spec,
        city=matched_city,
        gender=matched_gender,
        language=matched_lang,
        max_fee=matched_fee,
        date_intent=date_intent,
        confidence_score=0.85,
        summary=summary,
    )


def parse_natural_language_search(
    req: NLSearchRequest,
    db: Session,
    user_id: Optional[str] = None
) -> NLSearchResponse:
    """
    Parses natural language search queries to structured parameters and queries recommendations engine.
    """
    start_time = time.time()
    prompt = f"""
Extract structured appointment search filters from: "{req.query}"
Current City context: {req.current_city or 'None'}
Valid specialties: {json.dumps(VALID_SPECIALTIES)}
Valid cities: {json.dumps(VALID_CITIES)}

Return JSON:
- "specialty": matching valid specialty or null
- "city": matching valid city or null
- "hospital_name": hospital name if specified or null
- "gender": "female" or "male" or null
- "language": "Tamil", "English", or "Hindi" or null
- "max_fee": maximum consultation fee as float/int or null
- "date_intent": "today", "tomorrow", "this_weekend", "next_week", or null
- "summary": 1-line clean summary of extracted filters
"""
    system_instruction = "You are a healthcare appointment search filter extractor. Output JSON strictly conforming to the requested schema."

    llm_res = gemini_client.generate_json(prompt=prompt, system_instruction=system_instruction)
    is_fallback = False

    if llm_res and isinstance(llm_res, dict):
        spec = llm_res.get("specialty")
        if spec not in VALID_SPECIALTIES:
            spec = None
        city = llm_res.get("city")
        if city not in VALID_CITIES:
            city = None
        gender = llm_res.get("gender")
        if gender not in ["female", "male"]:
            gender = None
        lang = llm_res.get("language")
        max_fee = llm_res.get("max_fee")
        try:
            max_fee = float(max_fee) if max_fee is not None else None
        except (ValueError, TypeError):
            max_fee = None
        date_intent = llm_res.get("date_intent")
        summary = llm_res.get("summary", "Search filter parsed")

        filters = NLSearchFilterResult(
            specialty=spec,
            city=city,
            hospital_name=llm_res.get("hospital_name"),
            gender=gender,
            language=lang,
            max_fee=max_fee,
            date_intent=date_intent,
            confidence_score=0.95,
            summary=summary,
        )
        status_label = "success"
    else:
        is_fallback = True
        filters = _deterministic_extract_filters(req.query)
        status_label = "fallback"

    # Query recommendation engine with extracted filters
    recommended_docs = recommend_doctors(
        db=db,
        specialty=filters.specialty,
        city=filters.city,
        gender=filters.gender,
        max_fee=filters.max_fee,
        language=filters.language,
        limit=10,
    )

    top_doctor_ids = [doc.doctor_id for doc in recommended_docs]

    latency = int((time.time() - start_time) * 1000)
    _log_interaction(
        db=db,
        user_id=user_id,
        feature_type="nl_search",
        input_text=req.query,
        red_flag=False,
        urgency="routine",
        entities=filters.model_dump(),
        raw_response=llm_res,
        latency_ms=latency,
        status=status_label,
    )

    return NLSearchResponse(
        filters=filters,
        raw_query=req.query,
        is_fallback=is_fallback,
        matched_doctors_count=len(recommended_docs),
        top_doctor_ids=top_doctor_ids,
    )


def chat_with_assistant(
    req: AIChatRequest,
    db: Session,
    user_id: Optional[str] = None
) -> AIChatResponse:
    """
    Conversational Patient Booking Assistant.
    Adheres strictly to the human-in-the-loop rule:
    Generates a structured BookingProposal; DOES NOT auto-commit mutations.
    """
    start_time = time.time()
    if not req.messages:
        return AIChatResponse(message="Hello! I am MediSlot's AI Assistant. How can I help you today?")

    latest_msg = req.messages[-1].content
    lower = latest_msg.lower()

    # Step 1: Red-flag check on latest message
    is_emergency, matched_patterns, category = check_red_flags(latest_msg)
    if is_emergency:
        latency = int((time.time() - start_time) * 1000)
        _log_interaction(
            db=db,
            user_id=user_id,
            feature_type="booking_assistant",
            input_text=latest_msg,
            red_flag=True,
            urgency="emergency",
            entities={"category": category, "matched_patterns": matched_patterns},
            raw_response={"status": "emergency_blocked"},
            latency_ms=latency,
            status="emergency_blocked",
        )
        return AIChatResponse(
            message=EMERGENCY_INSTRUCTIONS,
            red_flag_triggered=True,
            urgency_level="emergency",
            suggested_action="emergency",
            emergency_protocol={
                "helplines": EMERGENCY_HELPLINES,
                "instructions": EMERGENCY_INSTRUCTIONS,
            },
            is_fallback=False,
        )

    # Step 2: Check if user is asking about their own appointments
    if any(k in lower for k in ["my appointment", "my booking", "when is my visit", "status of my"]):
        if user_id:
            from app.models.patient import Patient
            patient = db.query(Patient).filter(Patient.user_id == user_id).first()
            if patient:
                now = datetime.now(timezone.utc)
                active_appts = db.query(Appointment).filter(
                    Appointment.patient_id == patient.id,
                    Appointment.status.in_(["booked", "checked_in", "in_consultation"])
                ).order_by(Appointment.scheduled_start.asc()).all()

                if active_appts:
                    appt = active_appts[0]
                    ist_time = convert_utc_to_ist_str(appt.scheduled_start)
                    doc_name = appt.doctor.user.full_name if appt.doctor and appt.doctor.user else "Doctor"
                    msg = (
                        f"You have an upcoming appointment with **{doc_name}** ({appt.doctor.specialty}) "
                        f"on **{ist_time}** at **{appt.hospital.name if appt.hospital else 'Hospital'}**. "
                        f"Status: **{appt.status.upper()}**."
                    )
                    return AIChatResponse(
                        message=msg,
                        suggested_action="view_appointments",
                        urgency_level="routine",
                    )
                else:
                    return AIChatResponse(
                        message="You do not have any upcoming active appointments. Would you like me to help you find a doctor?",
                        suggested_action="consult_specialist",
                    )

    # Step 3: Triage symptoms / Find doctor
    # Extract query intent
    filter_result = _deterministic_extract_filters(latest_msg)
    target_spec = filter_result.specialty

    # If no specialty extracted, try triage
    if not target_spec:
        triage_res = triage_patient_symptoms(TriageRequest(symptoms=latest_msg), db=db, user_id=user_id)
        target_spec = triage_res.primary_specialty or "General Medicine"

    # Query matching doctors
    doctors = recommend_doctors(
        db=db,
        specialty=target_spec,
        city=filter_result.city,
        gender=filter_result.gender,
        max_fee=filter_result.max_fee,
        limit=3,
    )

    if not doctors:
        # Fallback to any doctor in specialty
        doctors = recommend_doctors(db=db, specialty=target_spec, limit=3)

    if doctors:
        top_doc_score = doctors[0]
        doc_obj = db.query(Doctor).filter(Doctor.id == top_doc_score.doctor_id).first()
        doc_name = doc_obj.user.full_name if doc_obj and doc_obj.user else "Doctor"

        # Check for upcoming available slots
        now = datetime.now(timezone.utc)
        target_date = (now + timedelta(days=1)).date()
        smart_slots_res = rank_slots_for_doctor(
            doctor_id=top_doc_score.doctor_id,
            target_date=target_date,
            db=db
        )

        proposal = None
        if smart_slots_res.suggested_slots:
            best_slot = smart_slots_res.suggested_slots[0]
            primary_aff = next((aff for aff in doc_obj.hospitals if aff.is_primary), doc_obj.hospitals[0] if doc_obj.hospitals else None)
            hosp_name = primary_aff.hospital.name if primary_aff and primary_aff.hospital else "MediSlot Partner Hospital"
            hosp_city = primary_aff.hospital.city if primary_aff and primary_aff.hospital else "Coimbatore"
            fee = primary_aff.consultation_fee if primary_aff else doc_obj.default_consultation_fee

            proposal = BookingProposal(
                doctor_id=top_doc_score.doctor_id,
                doctor_name=doc_name,
                specialty=doc_obj.specialty,
                hospital_name=hosp_name,
                hospital_city=hosp_city,
                slot_id=best_slot.id,
                slot_start_time=best_slot.slot_start_ist,
                consultation_fee=fee,
                reason=f"Top-rated {doc_obj.specialty} match with optimal slot ({getattr(best_slot, 'suggestion_reason', None) or 'Prime morning window'})",
            )

            msg = (
                f"Based on your symptoms, I recommend consulting **{doc_name}**, a verified {doc_obj.specialty} specialist "
                f"at {hosp_name} ({top_doc_score.explanation}).\n\n"
                f"I've identified an optimal slot for you: **{best_slot.slot_start_ist}**.\n\n"
                f"Please review the proposal card below and click **'Confirm & Book Slot'** to proceed."
            )
            suggested_action = "book_slot"
        else:
            msg = (
                f"I recommend consulting **{doc_name}** ({doc_obj.specialty}) at {doc_obj.qualification}. "
                f"Slots for tomorrow are currently full. Would you like to check other dates or join the waitlist?"
            )
            suggested_action = "consult_specialist"

        latency = int((time.time() - start_time) * 1000)
        _log_interaction(
            db=db,
            user_id=user_id,
            feature_type="booking_assistant",
            input_text=latest_msg,
            red_flag=False,
            urgency="routine",
            entities={"doctor_id": top_doc_score.doctor_id, "specialty": target_spec},
            raw_response={"proposal": proposal.model_dump() if proposal else None},
            latency_ms=latency,
            status="success",
            tools_called=["get_doctor_recommendations", "rank_slots_for_doctor"],
        )

        return AIChatResponse(
            message=msg,
            red_flag_triggered=False,
            urgency_level="routine",
            suggested_action=suggested_action,
            specialty_recommendation=target_spec,
            booking_proposal=proposal,
            is_fallback=False,
        )

    # If no doctors found at all
    return AIChatResponse(
        message=f"I couldn't locate an available doctor for {target_spec}. Please browse our doctors catalog or contact our patient support desk at 1800-MEDISLOT.",
        urgency_level="routine",
        suggested_action="consult_specialist",
    )
