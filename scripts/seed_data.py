import sys
import os
import random
from datetime import datetime, date, time, timezone, timedelta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User
from app.models.hospital import Hospital, Department
from app.models.doctor import Doctor, DoctorHospital
from app.models.patient import Patient
from app.models.schedule import WeeklyAvailabilityTemplate

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    try:
        print("Starting deterministic MediSlot database seeding...")
        random.seed(42)  # Deterministic seed

        # Check if already seeded
        if db.query(Hospital).count() >= 4 and db.query(Doctor).count() >= 40:
            print("Database already contains seeded data. Skipping re-seed.")
            return

        # 1. Super Admin
        admin_pass = hash_password("Admin@123456")
        hospital_admin_pass = hash_password("Hospital@123456")
        doctor_pass = hash_password("Doctor@123456")
        patient_pass = hash_password("Patient@123456")

        super_admin = db.query(User).filter(User.email == "admin@medislot.com").first()
        if not super_admin:
            super_admin = User(
                email="admin@medislot.com",
                password_hash=admin_pass,
                full_name="MediSlot Super Admin",
                phone="+919876543210",
                role="super_admin",
                is_active=True,
                is_verified=True
            )
            db.add(super_admin)
            db.flush()
            print("Created Super Admin: admin@medislot.com")

        # 2. 4 Fictional Hospitals in Western Tamil Nadu
        hospitals_data = [
            {
                "name": "Kovai Apex Medical Center",
                "slug": "kovai-apex-medical-center",
                "address": "142 Avinashi Road, Peelamedu",
                "city": "Coimbatore",
                "state": "Tamil Nadu",
                "postal_code": "641004",
                "phone": "+914222591001",
                "email": "contact@kovaiapex.org",
                "latitude": 11.0285,
                "longitude": 77.0044,
                "admin_email": "admin.coimbatore@medislot.com",
                "admin_name": "Coimbatore Hospital Admin"
            },
            {
                "name": "Cauvery Valley General Hospital",
                "slug": "cauvery-valley-general-hospital",
                "address": "88 Perundurai Main Road",
                "city": "Erode",
                "state": "Tamil Nadu",
                "postal_code": "638011",
                "phone": "+914242251002",
                "email": "contact@cauveryvalley.org",
                "latitude": 11.3320,
                "longitude": 77.7210,
                "admin_email": "admin.erode@medislot.com",
                "admin_name": "Erode Hospital Admin"
            },
            {
                "name": "Kongu Metro Healthcare",
                "slug": "kongu-metro-healthcare",
                "address": "55 Palladam Road, Thennampalayam",
                "city": "Tiruppur",
                "state": "Tamil Nadu",
                "postal_code": "641604",
                "phone": "+914212231003",
                "email": "contact@kongumetro.org",
                "latitude": 11.1015,
                "longitude": 77.3490,
                "admin_email": "admin.tiruppur@medislot.com",
                "admin_name": "Tiruppur Hospital Admin"
            },
            {
                "name": "Amaravathi Care Hospital",
                "slug": "amaravathi-care-hospital",
                "address": "22 Kangeyam Bypass Road",
                "city": "Dharapuram",
                "state": "Tamil Nadu",
                "postal_code": "638656",
                "phone": "+914258221004",
                "email": "contact@amaravathicare.org",
                "latitude": 10.7320,
                "longitude": 77.5310,
                "admin_email": "admin.dharapuram@medislot.com",
                "admin_name": "Dharapuram Hospital Admin"
            }
        ]

        hospitals = []
        for h_info in hospitals_data:
            hosp = db.query(Hospital).filter(Hospital.slug == h_info["slug"]).first()
            if not hosp:
                hosp = Hospital(
                    name=h_info["name"],
                    slug=h_info["slug"],
                    address=h_info["address"],
                    city=h_info["city"],
                    state=h_info["state"],
                    postal_code=h_info["postal_code"],
                    phone=h_info["phone"],
                    email=h_info["email"],
                    latitude=h_info["latitude"],
                    longitude=h_info["longitude"],
                    is_active=True
                )
                db.add(hosp)
                db.flush()

                # Create scoped Hospital Admin user
                h_admin = User(
                    email=h_info["admin_email"],
                    password_hash=hospital_admin_pass,
                    full_name=h_info["admin_name"],
                    phone=f"+9142{random.randint(10000000, 99999999)}",
                    role="hospital_admin",
                    hospital_id=hosp.id,
                    is_active=True,
                    is_verified=True
                )
                db.add(h_admin)
                db.flush()
                print(f"Created Hospital: {hosp.name} & Admin: {h_info['admin_email']}")

            hospitals.append(hosp)

        # 3. 10 Specialties & Departments per hospital
        specialties = [
            ("Cardiology", "Specialized care for heart conditions, hypertension, and cardiovascular health."),
            ("Dermatology", "Expert skin, hair, and nail treatments and cosmetic consultations."),
            ("Orthopedics", "Bone, joint, spine disorders, trauma surgery, and sports injuries."),
            ("Pediatrics", "Comprehensive child care, neonatal wellness, and immunizations."),
            ("Neurology", "Diagnosis and treatment of brain, spine, and nerve disorders."),
            ("Gynecology", "Women's reproductive health, maternity, and prenatal care."),
            ("Ophthalmology", "Advanced eye examinations, vision correction, and cataract care."),
            ("General Medicine", "Primary outpatient care, chronic disease management, and internal medicine."),
            ("Gastroenterology", "Digestive health, liver care, endoscopy, and stomach disorders."),
            ("ENT", "Ear, nose, throat, head, and neck clinical consultations.")
        ]

        hospital_departments = {}  # (hospital_id, specialty) -> Department
        for hosp in hospitals:
            for spec_name, spec_desc in specialties:
                dept = db.query(Department).filter(
                    Department.hospital_id == hosp.id,
                    Department.name == spec_name
                ).first()
                if not dept:
                    dept = Department(
                        hospital_id=hosp.id,
                        name=spec_name,
                        description=spec_desc,
                        is_active=True
                    )
                    db.add(dept)
                    db.flush()
                hospital_departments[(hosp.id, spec_name)] = dept

        # 4. 40 Fictional Doctors across the 10 specialties (4 doctors per specialty)
        doctor_first_names = [
            "Anand", "Bhuvanesh", "Chitra", "Deepa", "Elango", "Fathima", "Gokul", "Harish",
            "Indira", "Jagan", "Karthik", "Lakshmi", "Manoj", "Naveen", "Omprakash", "Pooja",
            "Qadir", "Rajesh", "Sangeetha", "Thangavel", "Uma", "Vignesh", "Wasim", "Yuvraj",
            "Zoya", "Arun", "Balaji", "Divya", "Ganesh", "Hemalatha", "Jayanth", "Keerthi",
            "Meenakshi", "Nandhini", "Prabhu", "Radhika", "Sivakumar", "Tarun", "Vidhya", "Yamuna"
        ]
        doctor_last_names = [
            "Sundaram", "Chandran", "Natarajan", "Ramaswamy", "Krishnan", "Subramanian",
            "Balasubramaniam", "Murugan", "Sengottaiyan", "Velmurugan", "Palanisamy", "Shanmugam"
        ]

        qualifications_pool = ["MBBS, MD", "MBBS, MS", "MBBS, DNB", "MBBS, MD, DM", "MBBS, MS, MCh"]
        languages_pool = [
            ["English", "Tamil"],
            ["English", "Tamil", "Hindi"],
            ["English", "Tamil", "Malayalam"],
            ["English", "Tamil", "Telugu"]
        ]

        doctors = []
        doctor_idx = 0
        for spec_idx, (spec_name, _) in enumerate(specialties):
            for i in range(4):
                doctor_idx += 1
                first = doctor_first_names[(doctor_idx - 1) % len(doctor_first_names)]
                last = doctor_last_names[(doctor_idx - 1) % len(doctor_last_names)]
                full_name = f"Dr. {first} {last}"
                email = f"doctor{doctor_idx}@medislot.com"
                phone = f"+9194{random.randint(10000000, 99999999)}"
                gender = "female" if (doctor_idx % 3 == 0) else "male"
                exp = random.randint(4, 25)
                fee = float(random.choice([400, 500, 600, 700, 800, 900]))
                rating = round(random.uniform(4.2, 4.9), 1)

                user = db.query(User).filter(User.email == email).first()
                if not user:
                    user = User(
                        email=email,
                        password_hash=doctor_pass,
                        full_name=full_name,
                        phone=phone,
                        role="doctor",
                        is_active=True,
                        is_verified=True
                    )
                    db.add(user)
                    db.flush()

                doc = db.query(Doctor).filter(Doctor.user_id == user.id).first()
                if not doc:
                    doc = Doctor(
                        user_id=user.id,
                        license_number=f"TNMC-{2000 + random.randint(1, 24)}-{random.randint(10000, 99999)}",
                        specialty=spec_name,
                        experience_years=exp,
                        qualification=random.choice(qualifications_pool),
                        bio=f"Senior consultant in {spec_name} with over {exp} years of clinical excellence in outpatient diagnostics and patient-centered care.",
                        languages_spoken=random.choice(languages_pool),
                        gender=gender,
                        default_consultation_fee=fee,
                        is_verified=True,
                        rating_avg=rating,
                        rating_count=random.randint(25, 240)
                    )
                    db.add(doc)
                    db.flush()

                    # Primary hospital affiliation
                    primary_hosp = hospitals[(doctor_idx - 1) % len(hospitals)]
                    primary_dept = hospital_departments.get((primary_hosp.id, spec_name))
                    aff1 = DoctorHospital(
                        doctor_id=doc.id,
                        hospital_id=primary_hosp.id,
                        department_id=primary_dept.id if primary_dept else None,
                        consultation_fee=fee,
                        room_number=f"OPD-{100 + doctor_idx}",
                        is_primary=True,
                        is_active=True
                    )
                    db.add(aff1)

                    # Multi-hospital practice: affiliate some doctors (e.g. 1 out of 3) with a second hospital
                    if doctor_idx % 3 == 0:
                        sec_hosp = hospitals[(doctor_idx) % len(hospitals)]
                        sec_dept = hospital_departments.get((sec_hosp.id, spec_name))
                        aff2 = DoctorHospital(
                            doctor_id=doc.id,
                            hospital_id=sec_hosp.id,
                            department_id=sec_dept.id if sec_dept else None,
                            consultation_fee=fee + 50.0,
                            room_number=f"Consultation-{200 + doctor_idx}",
                            is_primary=False,
                            is_active=True
                        )
                        db.add(aff2)

                    # Add recurring weekly availability schedule (Mon-Fri 09:00 - 13:00)
                    for day in range(0, 5):  # Mon-Fri
                        template = WeeklyAvailabilityTemplate(
                            doctor_id=doc.id,
                            hospital_id=primary_hosp.id,
                            day_of_week=day,
                            start_time=time(9, 0),
                            end_time=time(13, 0),
                            slot_duration_minutes=20,
                            is_active=True
                        )
                        db.add(template)

                doctors.append(doc)

        print(f"Created 40 Fictional Doctors across 10 Specialties with weekly schedules.")

        # 5. 500 Fictional Patients
        patient_first = [
            "Aakash", "Abhinav", "Ananya", "Bala", "Bhuvana", "Charan", "Deepak", "Devi",
            "Gautham", "Geetha", "Hari", "Harini", "Ishwarya", "Jeeva", "Kavya", "Keerthana",
            "Madhavan", "Malathi", "Naveen", "Nithya", "Pradeep", "Pravin", "Ramya", "Ranjith",
            "Sathish", "Sharmila", "Suresh", "Swetha", "Vasanth", "Vinodhini"
        ]
        patient_last = [
            "Kumar", "Rajan", "Palanisamy", "Subramanian", "Gopal", "Dharmalingam",
            "Kandasamy", "Muthusamy", "Ramanathan", "Loganathan", "Jayaram", "Viswanathan"
        ]
        blood_groups = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]

        created_patients = 0
        for p_idx in range(1, 501):
            p_email = f"patient{p_idx}@medislot.com"
            first = random.choice(patient_first)
            last = random.choice(patient_last)
            full_name = f"{first} {last}"
            phone = f"+919{random.randint(100000000, 999999999)}"
            gender = random.choice(["male", "female"])
            dob_year = random.randint(1955, 2012)
            dob_month = random.randint(1, 12)
            dob_day = random.randint(1, 28)

            user = db.query(User).filter(User.email == p_email).first()
            if not user:
                user = User(
                    email=p_email,
                    password_hash=patient_pass,
                    full_name=full_name,
                    phone=phone,
                    role="patient",
                    is_active=True,
                    is_verified=True
                )
                db.add(user)
                db.flush()

                patient = Patient(
                    user_id=user.id,
                    date_of_birth=date(dob_year, dob_month, dob_day),
                    gender=gender,
                    blood_group=random.choice(blood_groups),
                    emergency_contact_name=f"Guardian of {first}",
                    emergency_contact_phone=f"+919{random.randint(100000000, 999999999)}",
                    preferred_language=random.choice(["Tamil", "English"])
                )
                db.add(patient)
                created_patients += 1

        db.commit()
        print(f"Successfully seeded {created_patients} fictional patients.")
        print("Database seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed()
