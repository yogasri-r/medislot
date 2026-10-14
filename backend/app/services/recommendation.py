from datetime import datetime, timezone, timedelta, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models.doctor import Doctor, DoctorHospital
from app.models.hospital import Hospital
from app.models.schedule import Slot
from app.models.user import User
from app.services.availability import convert_utc_to_ist_str, IST_ZONE
from app.schemas.doctor import DoctorOut, DoctorHospitalOut
from app.schemas.recommendation import DoctorRecommendationScore

# Proximity matrix between Western Tamil Nadu healthcare clusters (normalized 0.0 to 1.0)
CITY_PROXIMITY = {
    ("coimbatore", "coimbatore"): 1.0,
    ("erode", "erode"): 1.0,
    ("tiruppur", "tiruppur"): 1.0,
    ("dharapuram", "dharapuram"): 1.0,
    ("coimbatore", "tiruppur"): 0.80,
    ("tiruppur", "coimbatore"): 0.80,
    ("tiruppur", "erode"): 0.75,
    ("erode", "tiruppur"): 0.75,
    ("tiruppur", "dharapuram"): 0.85,
    ("dharapuram", "tiruppur"): 0.85,
    ("coimbatore", "dharapuram"): 0.60,
    ("dharapuram", "coimbatore"): 0.60,
    ("coimbatore", "erode"): 0.55,
    ("erode", "coimbatore"): 0.55,
    ("erode", "dharapuram"): 0.65,
    ("dharapuram", "erode"): 0.65,
}

def _serialize_doctor(doc: Doctor) -> DoctorOut:
    affiliations = []
    for aff in doc.hospitals:
        affiliations.append(DoctorHospitalOut(
            id=aff.id,
            doctor_id=aff.doctor_id,
            hospital_id=aff.hospital_id,
            hospital_name=aff.hospital.name if aff.hospital else None,
            hospital_city=aff.hospital.city if aff.hospital else None,
            department_id=aff.department_id,
            department_name=aff.department.name if aff.department else None,
            consultation_fee=aff.consultation_fee,
            room_number=aff.room_number,
            is_primary=aff.is_primary,
            is_active=aff.is_active
        ))

    return DoctorOut(
        id=doc.id,
        user_id=doc.user_id,
        license_number=doc.license_number,
        specialty=doc.specialty,
        experience_years=doc.experience_years,
        qualification=doc.qualification,
        bio=doc.bio,
        languages_spoken=doc.languages_spoken,
        gender=doc.gender,
        default_consultation_fee=doc.default_consultation_fee,
        is_verified=doc.is_verified,
        rating_avg=float(doc.rating_avg),
        rating_count=doc.rating_count,
        user=doc.user,
        hospitals=affiliations
    )

def recommend_doctors(
    specialty: Optional[str] = None,
    city: Optional[str] = None,
    hospital_id: Optional[str] = None,
    language: Optional[str] = None,
    gender: Optional[str] = None,
    max_fee: Optional[float] = None,
    verified_only: bool = True,
    weights: Optional[Dict[str, float]] = None,
    limit: int = 10,
    db: Session = None
) -> List[DoctorRecommendationScore]:
    """
    Multi-factor doctor recommendation engine:
    Score = w1*specialty + w2*earliest_slot + w3*rating + w4*location + w5*experience + w6*language
    Default weights: specialty (0.30), earliest_slot (0.25), rating (0.20), location (0.15), experience (0.10)
    """
    if weights is None:
        weights = {
            "specialty": 0.30,
            "earliest_slot": 0.25,
            "rating": 0.20,
            "location": 0.15,
            "experience": 0.10
        }

    # Query doctors with eager loads
    query = db.query(Doctor).options(
        joinedload(Doctor.user),
        joinedload(Doctor.hospitals).joinedload(DoctorHospital.hospital),
        joinedload(Doctor.hospitals).joinedload(DoctorHospital.department)
    )

    if verified_only:
        query = query.filter(Doctor.is_verified == True)

    if specialty:
        query = query.filter(Doctor.specialty.ilike(f"%{specialty.strip()}%"))

    if gender:
        query = query.filter(Doctor.gender.ilike(gender.strip()))

    if hospital_id:
        query = query.join(DoctorHospital).filter(
            DoctorHospital.hospital_id == hospital_id,
            DoctorHospital.is_active == True
        )

    doctors = query.all()

    now = datetime.now(timezone.utc)
    lookahead_limit = now + timedelta(days=14)

    scored_doctors = []

    for doc in doctors:
        # 1. Specialty score
        spec_score = 1.0
        if specialty:
            if doc.specialty.lower() == specialty.strip().lower():
                spec_score = 1.0
            else:
                spec_score = 0.7

        # 2. Earliest available slot score
        earliest_slot = db.query(Slot).filter(
            Slot.doctor_id == doc.id,
            Slot.status == "available",
            Slot.slot_start >= now,
            Slot.slot_start <= lookahead_limit
        ).order_by(Slot.slot_start.asc()).first()

        earliest_slot_utc = None
        earliest_slot_ist = None
        if earliest_slot:
            earliest_slot_utc = earliest_slot.slot_start.isoformat()
            earliest_slot_ist = convert_utc_to_ist_str(earliest_slot.slot_start)
            hours_away = (earliest_slot.slot_start - now).total_seconds() / 3600.0

            if hours_away <= 24:
                slot_score = 1.0
            elif hours_away <= 48:
                slot_score = 0.85
            elif hours_away <= 96:
                slot_score = 0.70
            elif hours_away <= 168:
                slot_score = 0.50
            else:
                slot_score = 0.30
        else:
            slot_score = 0.05  # Penalty for no available slots in 14 days

        # 3. Rating score (Bayesian prior shrinkage of 4.0 with weight 5)
        # Prevents a doctor with 1 single 5-star review from beating a doctor with 200 reviews averaging 4.8
        rating_avg = doc.rating_avg or 4.0
        rating_cnt = doc.rating_count or 0
        bayesian_rating = (rating_avg * rating_cnt + 4.0 * 5) / (rating_cnt + 5)
        # Normalize 1.0 - 5.0 to 0.0 - 1.0
        rating_score = max(0.0, min(1.0, (bayesian_rating - 1.0) / 4.0))

        # 4. Location / City score
        loc_score = 1.0
        doc_cities = [aff.hospital.city.lower() for aff in doc.hospitals if aff.hospital]
        if city:
            req_city = city.strip().lower()
            best_city_score = 0.2
            for d_city in doc_cities:
                proximity = CITY_PROXIMITY.get((req_city, d_city), 0.3)
                if proximity > best_city_score:
                    best_city_score = proximity
            loc_score = best_city_score

        # 5. Experience score (linear scaling up to 25 years)
        exp_score = min(doc.experience_years / 25.0, 1.0)

        # 6. Language score
        lang_score = 1.0
        if language:
            spoken = [lang.lower() for lang in (doc.languages_spoken or [])]
            if any(language.lower() in s for s in spoken):
                lang_score = 1.0
            else:
                lang_score = 0.4

        # Fee constraint check
        if max_fee is not None and doc.default_consultation_fee > max_fee:
            continue

        # Composite weighted sum
        composite = (
            weights.get("specialty", 0.30) * spec_score +
            weights.get("earliest_slot", 0.25) * slot_score +
            weights.get("rating", 0.20) * rating_score +
            weights.get("location", 0.15) * loc_score +
            weights.get("experience", 0.10) * exp_score
        )

        # Small bonus for matching language
        if language and lang_score == 1.0:
            composite = min(1.0, composite + 0.05)

        # Generate human-readable explanation
        explanation_parts = []
        if earliest_slot_ist:
            explanation_parts.append(f"Next slot: {earliest_slot_ist}")
        else:
            explanation_parts.append("Next slot: Waitlist open")

        explanation_parts.append(f"{doc.rating_avg:.1f}★ ({doc.rating_count} reviews)")
        explanation_parts.append(f"{doc.experience_years} yrs exp")
        if doc.languages_spoken:
            explanation_parts.append(", ".join(doc.languages_spoken[:2]))

        explanation = " • ".join(explanation_parts)

        breakdown = {
            "specialty_match": round(spec_score, 2),
            "earliest_slot": round(slot_score, 2),
            "rating_normalized": round(rating_score, 2),
            "location_proximity": round(loc_score, 2),
            "experience": round(exp_score, 2),
            "language": round(lang_score, 2)
        }

        scored_doctors.append(DoctorRecommendationScore(
            doctor_id=doc.id,
            composite_score=round(composite, 3),
            score_breakdown=breakdown,
            explanation=explanation,
            earliest_available_slot_utc=earliest_slot_utc,
            earliest_available_slot_ist=earliest_slot_ist,
            doctor=_serialize_doctor(doc)
        ))

    # Sort descending by composite score
    scored_doctors.sort(key=lambda d: d.composite_score, reverse=True)
    return scored_doctors[:limit]
