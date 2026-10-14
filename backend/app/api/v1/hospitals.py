from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles, verify_hospital_access, log_audit
from app.models.user import User
from app.models.hospital import Hospital, Department
from app.models.doctor import Doctor, DoctorHospital
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.schemas.hospital import HospitalCreate, HospitalUpdate, HospitalOut, DepartmentCreate, DepartmentOut

router = APIRouter(prefix="/hospitals", tags=["Hospitals"])

@router.get("", response_model=List[HospitalOut])
def list_hospitals(city: Optional[str] = None, db: Session = Depends(get_db)):
    """Lists all active hospitals, optionally filtered by city."""
    query = db.query(Hospital).filter(Hospital.is_active == True)
    if city:
        query = query.filter(Hospital.city.ilike(f"%{city}%"))
    return query.order_by(Hospital.name).all()

@router.get("/network-analytics")
def get_super_admin_network_analytics(
    current_user: User = Depends(require_roles(["super_admin"])),
    db: Session = Depends(get_db)
):
    """Network-wide analytics across all hospitals for Super Admin."""
    hospitals = db.query(Hospital).filter(Hospital.is_active == True).all()
    doctors = db.query(Doctor).all()
    patients = db.query(Patient).all()
    all_appts = db.query(Appointment).all()

    total_appts = len(all_appts)
    completed_appts = sum(1 for a in all_appts if a.status == "completed")
    no_show_appts = sum(1 for a in all_appts if a.status == "no_show")
    network_no_show_rate = round((no_show_appts / total_appts * 100), 1) if total_appts > 0 else 0.0

    hosp_summaries = []
    for h in hospitals:
        h_appts = [a for a in all_appts if a.hospital_id == h.id]
        h_completed = sum(1 for a in h_appts if a.status == "completed")
        h_affs = db.query(DoctorHospital).filter(DoctorHospital.hospital_id == h.id, DoctorHospital.is_active == True).count()
        doc_fees = {d.id: d.default_consultation_fee for d in doctors}
        h_revenue = sum(doc_fees.get(a.doctor_id, 500.0) for a in h_appts if a.status == "completed")
        hosp_summaries.append({
            "id": h.id,
            "name": h.name,
            "city": h.city,
            "state": h.state,
            "phone": h.phone,
            "doctors_count": h_affs,
            "total_appointments": len(h_appts),
            "completed_appointments": h_completed,
            "estimated_revenue": h_revenue,
        })

    spec_counts = {}
    for doc in doctors:
        spec_counts[doc.specialty] = spec_counts.get(doc.specialty, 0) + 1

    return {
        "network_stats": {
            "total_hospitals": len(hospitals),
            "total_doctors": len(doctors),
            "verified_doctors": sum(1 for d in doctors if d.is_verified),
            "total_patients": len(patients),
            "total_appointments": total_appts,
            "completed_appointments": completed_appts,
            "network_no_show_rate": network_no_show_rate,
        },
        "hospitals": hosp_summaries,
        "specialties_distribution": spec_counts,
    }

@router.get("/{hospital_id}/dashboard-stats")
def get_hospital_dashboard_stats(
    hospital_id: str,
    current_user: User = Depends(require_roles(["super_admin", "hospital_admin"])),
    db: Session = Depends(get_db)
):
    """Hospital-scoped operational metrics and doctor roster for Hospital Admin."""
    verify_hospital_access(hospital_id, current_user)
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")

    affiliations = db.query(DoctorHospital).filter(
        DoctorHospital.hospital_id == hospital_id,
        DoctorHospital.is_active == True
    ).all()
    doctor_ids = [aff.doctor_id for aff in affiliations]

    appts = db.query(Appointment).filter(Appointment.hospital_id == hospital_id).all()
    total_appts = len(appts)
    completed_appts = sum(1 for a in appts if a.status == "completed")
    no_show_appts = sum(1 for a in appts if a.status == "no_show")
    cancelled_appts = sum(1 for a in appts if a.status == "cancelled")
    active_appts = sum(1 for a in appts if a.status in ["booked", "checked_in", "in_consultation"])

    no_show_rate = round((no_show_appts / total_appts * 100), 1) if total_appts > 0 else 0.0

    departments = db.query(Department).filter(Department.hospital_id == hospital_id).all()
    dept_stats = []
    for d in departments:
        docs_in_dept = sum(1 for aff in affiliations if aff.department_id == d.id)
        dept_stats.append({
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "doctors_count": docs_in_dept
        })

    docs = db.query(Doctor).filter(Doctor.id.in_(doctor_ids)).all() if doctor_ids else []
    doctor_stats = []
    for doc in docs:
        doc_appts = [a for a in appts if a.doctor_id == doc.id]
        doc_completed = sum(1 for a in doc_appts if a.status == "completed")
        doc_no_show = sum(1 for a in doc_appts if a.status == "no_show")
        aff = next((a for a in affiliations if a.doctor_id == doc.id), None)
        doctor_stats.append({
            "id": doc.id,
            "name": doc.user.full_name if doc.user else "Doctor",
            "email": doc.user.email if doc.user else "",
            "specialty": doc.specialty,
            "license_number": doc.license_number,
            "qualification": doc.qualification,
            "experience_years": doc.experience_years,
            "is_verified": doc.is_verified,
            "consultation_fee": aff.consultation_fee if aff else doc.default_consultation_fee,
            "rating_avg": float(doc.rating_avg),
            "rating_count": doc.rating_count,
            "total_appointments": len(doc_appts),
            "completed_appointments": doc_completed,
            "no_show_count": doc_no_show,
        })

    return {
        "hospital": {
            "id": hosp.id,
            "name": hosp.name,
            "city": hosp.city,
            "state": hosp.state,
            "address": hosp.address,
            "phone": hosp.phone,
            "email": hosp.email,
        },
        "stats": {
            "total_doctors": len(docs),
            "total_departments": len(departments),
            "total_appointments": total_appts,
            "active_appointments": active_appts,
            "completed_appointments": completed_appts,
            "no_show_appointments": no_show_appts,
            "cancelled_appointments": cancelled_appts,
            "no_show_rate": no_show_rate,
        },
        "departments": dept_stats,
        "doctors": doctor_stats,
    }

@router.get("/{hospital_id}", response_model=HospitalOut)
def get_hospital(hospital_id: str, db: Session = Depends(get_db)):
    """Gets details of a specific hospital."""
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    return hosp

@router.post("", response_model=HospitalOut, status_code=status.HTTP_201_CREATED)
def create_hospital(
    payload: HospitalCreate,
    current_user: User = Depends(require_roles(["super_admin"])),
    db: Session = Depends(get_db)
):
    """Adds a new hospital to the network (Super Admin only)."""
    existing = db.query(Hospital).filter(Hospital.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hospital slug already in use.")

    hosp = Hospital(**payload.model_dump())
    db.add(hosp)
    db.commit()
    db.refresh(hosp)
    log_audit(db, current_user.id, "CREATE", "hospital", hosp.id, hosp.id)
    return hosp

@router.put("/{hospital_id}", response_model=HospitalOut)
def update_hospital(
    hospital_id: str,
    payload: HospitalUpdate,
    current_user: User = Depends(require_roles(["super_admin", "hospital_admin"])),
    db: Session = Depends(get_db)
):
    """Updates hospital information. Hospital admins can only update their own hospital."""
    verify_hospital_access(hospital_id, current_user)
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(hosp, field, val)

    db.commit()
    db.refresh(hosp)
    log_audit(db, current_user.id, "UPDATE", "hospital", hosp.id, hosp.id)
    return hosp

@router.get("/{hospital_id}/departments", response_model=List[DepartmentOut])
def list_hospital_departments(hospital_id: str, db: Session = Depends(get_db)):
    """Lists departments for a specific hospital."""
    return db.query(Department).filter(
        Department.hospital_id == hospital_id,
        Department.is_active == True
    ).order_by(Department.name).all()

@router.post("/{hospital_id}/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    hospital_id: str,
    payload: DepartmentCreate,
    current_user: User = Depends(require_roles(["super_admin", "hospital_admin"])),
    db: Session = Depends(get_db)
):
    """Creates a department in the given hospital (hospital-scoped)."""
    verify_hospital_access(hospital_id, current_user)
    existing = db.query(Department).filter(
        Department.hospital_id == hospital_id,
        Department.name.ilike(payload.name)
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department already exists in this hospital.")

    dept = Department(
        hospital_id=hospital_id,
        name=payload.name,
        description=payload.description,
        is_active=True
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    log_audit(db, current_user.id, "CREATE_DEPARTMENT", "department", dept.id, hospital_id)
    return dept
