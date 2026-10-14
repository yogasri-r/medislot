from datetime import datetime, timezone, timedelta, date, time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.schedule import Slot
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.services.availability import get_slots_for_doctor, convert_utc_to_ist_str, IST_ZONE
from app.schemas.recommendation import SmartSlotOut, SmartSlotsResponse

def rank_slots_for_doctor(
    doctor_id: str,
    target_date: date,
    patient_id: Optional[str] = None,
    hospital_id: Optional[str] = None,
    db: Session = None
) -> SmartSlotsResponse:
    """
    Ranks available slots for a doctor on a target date.
    Highlights Top 3 'Suggested' slots based on:
    1. Patient preferred time of day (from historical bookings)
    2. Adjacent gap-filling (efficiently packing doctor's schedule)
    3. Late-day accumulated delay penalty
    4. Clinical load balancing
    """
    # Fetch all slots for this doctor on target date
    all_db_slots = get_slots_for_doctor(
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        target_date=target_date,
        db=db,
        auto_generate=True
    )

    if not all_db_slots:
        return SmartSlotsResponse(
            doctor_id=doctor_id,
            target_date=target_date.isoformat(),
            total_slots=0,
            available_slots=0,
            suggested_slots=[],
            all_slots=[]
        )

    # 1. Learn patient's historical preferred time of day
    preferred_hour_ist = 10.0  # Default neutral prior (10:00 AM)
    has_patient_history = False

    if patient_id:
        past_slots = db.query(Slot.slot_start).join(
            Appointment, Appointment.slot_id == Slot.id
        ).filter(
            Appointment.patient_id == patient_id,
            Appointment.status == "completed"
        ).all()

        if past_slots:
            hours = [s[0].astimezone(IST_ZONE).hour + (s[0].astimezone(IST_ZONE).minute / 60.0) for s in past_slots]
            preferred_hour_ist = sum(hours) / len(hours)
            has_patient_history = True

    # Map of all slot start times to status for adjacent checking
    slot_status_map = {s.slot_start: s.status for s in all_db_slots}

    scored_available_slots = []
    all_serialized_slots = []

    for slot in all_db_slots:
        slot_ist_dt = slot.slot_start.astimezone(IST_ZONE)
        slot_hour_ist = slot_ist_dt.hour + (slot_ist_dt.minute / 60.0)

        # Baseline score calculation for available slots
        if slot.status == "available":
            # Factor 1: Time of day preference (Gaussian falloff from preferred hour)
            hour_diff = abs(slot_hour_ist - preferred_hour_ist)
            pref_score = max(0.2, 1.0 - (hour_diff / 4.0))

            # Factor 2: Adjacent gap filling
            # Check slot 20 mins before and 20 mins after
            prev_t = slot.slot_start - timedelta(minutes=20)
            next_t = slot.slot_start + timedelta(minutes=20)
            is_prev_booked = slot_status_map.get(prev_t) == "booked"
            is_next_booked = slot_status_map.get(next_t) == "booked"

            if is_prev_booked and is_next_booked:
                gap_score = 1.0  # Fills an exact 20-min gap between 2 appointments!
            elif is_prev_booked or is_next_booked:
                gap_score = 0.85 # Extends a continuous block of consultations
            else:
                gap_score = 0.40 # Isolated slot

            # Factor 3: Accumulated delay risk penalty
            # Early morning (09:00 - 10:00): low delay risk (1.0)
            # Noon (12:00 - 13:00): higher accumulated delay risk (0.65)
            # Linearly decays from 09:00 to 13:00
            delay_risk_score = max(0.55, 1.0 - ((slot_hour_ist - 9.0) / 8.0))

            # Factor 4: Prime morning slot bonus (10:00 - 11:30 AM is peak patient energy)
            prime_bonus = 0.10 if (10.0 <= slot_hour_ist <= 11.5) else 0.0

            # Composite slot score (0.0 to 1.0)
            composite_slot_score = (
                0.35 * pref_score +
                0.30 * gap_score +
                0.25 * delay_risk_score +
                0.10 * (1.0 if not is_prev_booked and not is_next_booked else 0.5)
            ) + prime_bonus
            composite_slot_score = round(min(1.0, max(0.0, composite_slot_score)), 3)

            scored_available_slots.append((composite_slot_score, slot, gap_score, pref_score, delay_risk_score))
        else:
            composite_slot_score = 0.0

    # Sort available slots by score descending
    scored_available_slots.sort(key=lambda x: x[0], reverse=True)

    # Top 3 suggested slots
    top_3_slot_ids = set()
    suggestions_reasons = {}

    for idx, (score_val, s, gap_score, pref_score, delay_score) in enumerate(scored_available_slots[:3]):
        top_3_slot_ids.add(s.id)
        if idx == 0:
            if has_patient_history:
                reason = "Top Pick: Matches your preferred consultation time with low delay risk"
            else:
                reason = "Top Pick: Optimal morning consultation with minimal expected clinic delay"
        elif gap_score >= 0.85:
            reason = "Recommended: Adjacent to doctor's active consultation block"
        elif delay_score >= 0.85:
            reason = "Fast Intake: Early session slot with lowest probability of outpatient delays"
        else:
            reason = "Convenient mid-morning outpatient consultation slot"
        suggestions_reasons[s.id] = reason

    # Serialize all slots
    suggested_list = []
    for slot in all_db_slots:
        is_sugg = slot.id in top_3_slot_ids
        score_for_slot = next((sc[0] for sc in scored_available_slots if sc[1].id == slot.id), 0.0)
        reason_for_slot = suggestions_reasons.get(slot.id)

        serialized = SmartSlotOut(
            id=slot.id,
            doctor_id=slot.doctor_id,
            hospital_id=slot.hospital_id,
            slot_start=slot.slot_start.isoformat(),
            slot_end=slot.slot_end.isoformat(),
            slot_start_ist=convert_utc_to_ist_str(slot.slot_start),
            slot_end_ist=convert_utc_to_ist_str(slot.slot_end),
            status=slot.status,
            score=score_for_slot,
            is_suggested=is_sugg,
            suggestion_reason=reason_for_slot
        )
        all_serialized_slots.append(serialized)
        if is_sugg:
            suggested_list.append(serialized)

    # Sort suggested by start time
    suggested_list.sort(key=lambda x: x.slot_start)

    return SmartSlotsResponse(
        doctor_id=doctor_id,
        target_date=target_date.isoformat(),
        total_slots=len(all_db_slots),
        available_slots=len(scored_available_slots),
        suggested_slots=suggested_list,
        all_slots=all_serialized_slots
    )
