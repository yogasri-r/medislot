import sys
import os
import random
import uuid
from datetime import datetime, date, time, timezone, timedelta
import zoneinfo
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import SessionLocal
from app.models.doctor import Doctor, DoctorHospital
from app.models.hospital import Hospital
from app.models.patient import Patient
from app.models.schedule import Slot
from app.models.appointment import Appointment, DoctorRating

IST_ZONE = zoneinfo.ZoneInfo("Asia/Kolkata")

CANCELLATION_REASONS = [
    "Sudden personal emergency",
    "Feeling significantly better; symptoms resolved",
    "Work schedule conflict",
    "Transportation delay",
    "Rescheduled to another date",
    "Consulted another doctor locally",
    "Family medical commitment"
]

FEEDBACK_COMMENTS_5 = [
    "Excellent consultation. Doctor listened very patiently and explained everything clearly.",
    "Very knowledgeable and reassuring. Minimal waiting time.",
    "Outstanding diagnosis and clear prescription. Highly recommended!",
    "Great experience, doctor was very kind and addressed all my health concerns."
]

FEEDBACK_COMMENTS_4 = [
    "Good consultation, polite doctor and helpful staff.",
    "Doctor was thorough and professional. Slight delay in consultation start.",
    "Helpful diagnosis, clinic was clean and organized."
]

FEEDBACK_COMMENTS_3 = [
    "Doctor was rushed due to queue volume, but diagnosis was accurate.",
    "Average experience. Long wait time in outpatient waiting hall.",
    "Consultation was okay, expected more detailed diet explanation."
]

SPECIALTY_DURATION_OFFSET = {
    "Cardiology": 3.5,
    "Orthopedics": 2.5,
    "Neurology": 3.0,
    "Pediatrics": 1.0,
    "General Medicine": -1.5,
    "Dermatology": -2.5,
    "ENT": -1.0,
    "Gynecology": 2.0
}

def simulate_history(days: int = 180, appointments_per_day: int = 25, force: bool = False):
    """
    Simulates realistic historical appointment records across Western Tamil Nadu hospitals:
    - Clinically realistic no-show risk conditioned on lead time, patient trait, appointment type, age, and history.
    - Realistic consultation durations conditioned on appointment type, specialty, and doctor experience.
    """
    db = SessionLocal()
    try:
        random.seed(42)  # Deterministic seed

        total_existing_appts = db.query(Appointment).count()
        if total_existing_appts >= 1500 and not force:
            print(f"Database already has {total_existing_appts} historical appointments. Skipping simulation (use --force to re-generate).")
            return

        if force:
            print("Force flag detected. Purging previous simulated historical records...")
            db.execute(text("DELETE FROM doctor_ratings WHERE id IS NOT NULL;"))
            db.execute(text("DELETE FROM reminder_jobs WHERE id IS NOT NULL;"))
            db.execute(text("DELETE FROM notifications WHERE id IS NOT NULL;"))
            db.execute(text("DELETE FROM appointments WHERE appointment_number LIKE 'MED-%';"))
            db.execute(text("DELETE FROM slots WHERE status = 'booked' AND slot_start < NOW();"))
            db.commit()
            print("Purged old historical appointments and ratings.")

        print(f"Starting clinically calibrated historical appointment simulation for past {days} days...")

        doctors = db.query(Doctor).filter(Doctor.is_verified == True).all()
        patients = db.query(Patient).all()
        if not doctors or not patients:
            print("Doctors or patients missing in database. Please run seed_data.py first.")
            return

        # Pre-assign inherent patient adherence tendencies
        patient_adherence = {}
        for p in patients:
            p_rand = random.Random(p.id)
            # 60% highly adherent, 25% moderate, 15% chronic no-show
            base_risk = p_rand.choices([0.05, 0.12, 0.22, 0.45], weights=[60, 25, 10, 5])[0]
            patient_adherence[p.id] = {
                "base_risk": base_risk,
                "past_no_shows": 0,
                "past_total": 0
            }

        today = date.today()
        start_date = today - timedelta(days=days)

        created_slots = 0
        created_appts = 0
        created_ratings = 0

        # Pre-query primary doctor hospital map
        doc_hosp_map = {}
        for doc in doctors:
            aff = db.query(DoctorHospital).filter(
                DoctorHospital.doctor_id == doc.id,
                DoctorHospital.is_primary == True
            ).first()
            if not aff:
                aff = db.query(DoctorHospital).filter(DoctorHospital.doctor_id == doc.id).first()
            if aff:
                doc_hosp_map[doc.id] = aff.hospital_id

        # Loop day by day
        curr_date = start_date
        while curr_date < today:
            # Skip weekends (outpatient clinic shifts are Mon-Fri)
            if curr_date.weekday() >= 5:
                curr_date += timedelta(days=1)
                continue

            # Pick a subset of doctors working today
            active_docs = random.sample(doctors, k=min(len(doctors), 18))

            for doc in active_docs:
                hosp_id = doc_hosp_map.get(doc.id)
                if not hosp_id:
                    continue

                # Shift: 09:00 to 13:00 IST (12 slots of 20 mins)
                num_slots = random.randint(4, 8)
                available_times = [
                    time(9, 0), time(9, 20), time(9, 40),
                    time(10, 0), time(10, 20), time(10, 40),
                    time(11, 0), time(11, 20), time(11, 40),
                    time(12, 0), time(12, 20), time(12, 40)
                ]
                booked_times = random.sample(available_times, k=num_slots)
                booked_times.sort()

                accumulated_delay = 0

                for slot_t in booked_times:
                    # Convert to UTC
                    local_dt = datetime.combine(curr_date, slot_t, tzinfo=IST_ZONE)
                    utc_start = local_dt.astimezone(timezone.utc)
                    utc_end = utc_start + timedelta(minutes=20)

                    # Create Slot record
                    slot = Slot(
                        doctor_id=doc.id,
                        hospital_id=hosp_id,
                        slot_start=utc_start,
                        slot_end=utc_end,
                        status="booked"
                    )
                    db.add(slot)
                    db.flush()
                    created_slots += 1

                    # Pick patient
                    patient = random.choice(patients)
                    p_state = patient_adherence[patient.id]
                    appt_type = "new_patient" if random.random() < 0.60 else "follow_up"
                    est_duration = 25 if appt_type == "new_patient" else 15

                    # Lead time in days (1 to 21 days)
                    lead_time_days = random.randint(1, 21)
                    booking_created_at = utc_start - timedelta(days=lead_time_days)

                    # Causal No-Show Probability:
                    # 1. Base patient risk trait
                    prob_no_show = p_state["base_risk"]
                    # 2. Lead time effect (+1.2% per day of advance booking)
                    prob_no_show += 0.012 * min(lead_time_days, 18)
                    # 3. Appointment type effect (+8% for new patient, -4% for established follow-up)
                    prob_no_show += (0.08 if appt_type == "new_patient" else -0.04)
                    # 4. Chronic no-show history effect (+15% if patient previously failed to attend)
                    if p_state["past_total"] > 0 and (p_state["past_no_shows"] / p_state["past_total"]) > 0.30:
                        prob_no_show += 0.15
                    # 5. Clamp to realistic clinical bounds [0.03, 0.88]
                    prob_no_show = max(0.03, min(0.88, prob_no_show))

                    outcome_rand = random.random()
                    if outcome_rand < prob_no_show:
                        status_val = "no_show"
                        p_state["past_no_shows"] += 1
                    else:
                        # Of remaining non-no-shows, ~12% cancel in advance, remainder attend
                        if random.random() < 0.13:
                            status_val = "cancelled"
                        else:
                            status_val = "completed"
                    
                    p_state["past_total"] += 1

                    # Causal Consultation Duration:
                    # Base: 22 mins for new patients, 14.5 mins for follow-ups
                    base_dur = 22.0 if appt_type == "new_patient" else 14.5
                    spec_offset = SPECIALTY_DURATION_OFFSET.get(doc.specialty, 0.0)
                    exp_offset = -0.12 * min(doc.experience_years, 20)
                    jitter = random.gauss(0.0, 2.8)
                    actual_duration = int(round(max(8, min(45, base_dur + spec_offset + exp_offset + jitter))))

                    # Compute timestamps
                    if status_val == "completed":
                        # Arrived 5-15 mins early
                        check_in_offset = random.randint(5, 15)
                        check_in = utc_start - timedelta(minutes=check_in_offset)
                        
                        # Consultation starts with accumulated clinic delay
                        consult_start = utc_start + timedelta(minutes=accumulated_delay)
                        consult_end = consult_start + timedelta(minutes=actual_duration)

                        # Update accumulated delay for next patient in clinic
                        delta_mins = actual_duration - 20
                        accumulated_delay = max(0, min(60, accumulated_delay + delta_mins))

                        actual_wait = max(0, int((consult_start - check_in).total_seconds() / 60.0))

                        appt = Appointment(
                            appointment_number=f"MED-{curr_date.strftime('%Y%m%d')}-{created_appts:05d}-{uuid.uuid4().hex[:8].upper()}",
                            slot_id=slot.id,
                            doctor_id=doc.id,
                            hospital_id=hosp_id,
                            patient_id=patient.id,
                            appointment_type=appt_type,
                            status="completed",
                            check_in_time=check_in,
                            consultation_start_time=consult_start,
                            consultation_end_time=consult_end,
                            actual_duration_minutes=actual_duration,
                            estimated_duration_minutes=est_duration,
                            estimated_wait_minutes=actual_wait,
                            created_at=booking_created_at
                        )
                        db.add(appt)
                        db.flush()
                        created_appts += 1

                        # ~35% patients leave a review
                        if random.random() < 0.35:
                            r_val = random.choices([5, 4, 3, 2, 1], weights=[50, 35, 10, 3, 2])[0]
                            if r_val == 5:
                                comment = random.choice(FEEDBACK_COMMENTS_5)
                            elif r_val == 4:
                                comment = random.choice(FEEDBACK_COMMENTS_4)
                            else:
                                comment = random.choice(FEEDBACK_COMMENTS_3)

                            review = DoctorRating(
                                appointment_id=appt.id,
                                doctor_id=doc.id,
                                patient_id=patient.id,
                                rating=r_val,
                                review_text=comment,
                                is_moderated=True,
                                moderation_status="approved",
                                moderated_at=consult_end + timedelta(hours=2),
                                created_at=consult_end + timedelta(hours=1)
                            )
                            db.add(review)
                            created_ratings += 1

                    elif status_val == "no_show":
                        appt = Appointment(
                            appointment_number=f"MED-{curr_date.strftime('%Y%m%d')}-{created_appts:05d}-{uuid.uuid4().hex[:8].upper()}",
                            slot_id=slot.id,
                            doctor_id=doc.id,
                            hospital_id=hosp_id,
                            patient_id=patient.id,
                            appointment_type=appt_type,
                            status="no_show",
                            estimated_duration_minutes=est_duration,
                            created_at=booking_created_at
                        )
                        db.add(appt)
                        created_appts += 1

                    else:  # cancelled
                        appt = Appointment(
                            appointment_number=f"MED-{curr_date.strftime('%Y%m%d')}-{created_appts:05d}-{uuid.uuid4().hex[:8].upper()}",
                            slot_id=slot.id,
                            doctor_id=doc.id,
                            hospital_id=hosp_id,
                            patient_id=patient.id,
                            appointment_type=appt_type,
                            status="cancelled",
                            cancellation_reason=random.choice(CANCELLATION_REASONS),
                            estimated_duration_minutes=est_duration,
                            created_at=booking_created_at
                        )
                        db.add(appt)
                        created_appts += 1

            curr_date += timedelta(days=1)
            # Periodic batch commit every 15 days
            if (curr_date - start_date).days % 15 == 0:
                db.commit()
                print(f"  Progress: {(curr_date - start_date).days}/{days} days simulated ({created_appts} appointments)...")

        # Update doctor aggregate ratings based on actual reviews
        print("Recalculating verified doctor ratings from simulated history...")
        for doc in doctors:
            ratings = db.query(DoctorRating).filter(
                DoctorRating.doctor_id == doc.id,
                DoctorRating.moderation_status == "approved"
            ).all()
            if ratings:
                avg = sum(r.rating for r in ratings) / len(ratings)
                doc.rating_avg = round(avg, 2)
                doc.rating_count = len(ratings)

        db.commit()
        print(f"\nSimulation complete!")
        print(f"Total Slots Created       : {created_slots}")
        print(f"Total Appointments Created: {created_appts}")
        print(f"Total Patient Ratings     : {created_ratings}")

    except Exception as ex:
        db.rollback()
        print(f"Error during history simulation: {ex}")
        raise ex
    finally:
        db.close()

if __name__ == "__main__":
    force_run = "--force" in sys.argv
    simulate_history(days=180, force=force_run)
