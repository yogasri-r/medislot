import sys
import os
import random
import uuid
from datetime import datetime, date, time, timezone, timedelta
import zoneinfo

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

def simulate_history(days: int = 180, appointments_per_day: int = 25):
    """
    Simulates realistic historical appointment records across Western Tamil Nadu hospitals:
    - Log-normal consultation duration distribution (mean ~ 18 mins, sigma 0.35).
    - Status distribution: ~70% completed, ~18% no-show, ~12% cancelled.
    - Realistic arrival offsets, check-in timestamps, and doctor reviews.
    """
    db = SessionLocal()
    try:
        random.seed(42)  # Deterministic seed

        total_existing_appts = db.query(Appointment).count()
        if total_existing_appts >= 1500:
            print(f"Database already has {total_existing_appts} historical appointments. Skipping simulation.")
            return

        print(f"Starting historical appointment simulation for past {days} days...")

        doctors = db.query(Doctor).filter(Doctor.is_verified == True).all()
        patients = db.query(Patient).all()
        if not doctors or not patients:
            print("Doctors or patients missing in database. Please run seed_data.py first.")
            return

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
            # Skip weekends (doctors outpatient shifts are Mon-Fri)
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
                # Pick 4 to 8 bookings per doctor per working day
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
                    appt_type = "new_patient" if random.random() < 0.60 else "follow_up"
                    est_duration = 25 if appt_type == "new_patient" else 15

                    # Outcome distribution: 70% completed, 18% no-show, 12% cancelled
                    outcome_rand = random.random()
                    if outcome_rand < 0.70:
                        status_val = "completed"
                    elif outcome_rand < 0.88:
                        status_val = "no_show"
                    else:
                        status_val = "cancelled"

                    # Log-normal distribution for consultation duration:
                    # mu = 2.89 (exp(2.89) ≈ 18 mins), sigma = 0.35
                    raw_duration = random.lognormvariate(mu=2.89, sigma=0.35)
                    actual_duration = int(round(max(8, min(45, raw_duration))))

                    # Compute timestamps
                    if status_val == "completed":
                        # Arrived 5-15 mins early
                        check_in_offset = random.randint(5, 15)
                        check_in = utc_start - timedelta(minutes=check_in_offset)
                        
                        # Consultation starts with accumulated delay
                        consult_start = utc_start + timedelta(minutes=accumulated_delay)
                        consult_end = consult_start + timedelta(minutes=actual_duration)

                        # Update accumulated delay for next patient in clinic
                        # If consultation took longer than 20 mins, delay accumulates
                        delta_mins = actual_duration - 20
                        accumulated_delay = max(0, min(60, accumulated_delay + delta_mins))

                        actual_wait = max(0, int((consult_start - check_in).total_seconds() / 60.0))

                        appt = Appointment(
                            appointment_number=f"MED-{curr_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
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
                            created_at=utc_start - timedelta(days=random.randint(1, 14))
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
                            appointment_number=f"MED-{curr_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                            slot_id=slot.id,
                            doctor_id=doc.id,
                            hospital_id=hosp_id,
                            patient_id=patient.id,
                            appointment_type=appt_type,
                            status="no_show",
                            estimated_duration_minutes=est_duration,
                            created_at=utc_start - timedelta(days=random.randint(1, 14))
                        )
                        db.add(appt)
                        created_appts += 1

                    else:  # cancelled
                        appt = Appointment(
                            appointment_number=f"MED-{curr_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                            slot_id=slot.id,
                            doctor_id=doc.id,
                            hospital_id=hosp_id,
                            patient_id=patient.id,
                            appointment_type=appt_type,
                            status="cancelled",
                            cancellation_reason=random.choice(CANCELLATION_REASONS),
                            estimated_duration_minutes=est_duration,
                            created_at=utc_start - timedelta(days=random.randint(2, 14))
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
    simulate_history(days=180)
