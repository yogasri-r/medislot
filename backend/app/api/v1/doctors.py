from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles, verify_hospital_access, log_audit
from app.models.user import User
from app.models.doctor import Doctor, DoctorHospital
from app.models.hospital import Hospital, Department
from app.schemas.doctor import DoctorCreate, DoctorUpdate, DoctorOut, DoctorHospitalLink, DoctorHospitalOut

router = APIRouter(prefix="/doctors", tags=["Doctors"])

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

@router.get("", response_model=List[DoctorOut])
def search_doctors(
    specialty: Optional[str] = None,
    city: Optional[str] = None,
    hospital_id: Optional[str] = None,
    language: Optional[str] = None,
    gender: Optional[str] = None,
    verified_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Searches doctors by specialty, city, hospital, language, gender, and verification status.
    Hospital selection is fully optional.
    """
    query = db.query(Doctor).options(
        joinedload(Doctor.user),
        joinedload(Doctor.hospitals).joinedload(DoctorHospital.hospital),
        joinedload(Doctor.hospitals).joinedload(DoctorHospital.department)
    )

    if verified_only:
        query = query.filter(Doctor.is_verified == True)
    if specialty:
        query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
    if gender:
        query = query.filter(Doctor.gender.ilike(gender))
    if hospital_id:
        query = query.join(DoctorHospital).filter(
            DoctorHospital.hospital_id == hospital_id,
            DoctorHospital.is_active == True
        )
    elif city:
        query = query.join(DoctorHospital).join(Hospital).filter(
            Hospital.city.ilike(f"%{city}%"),
            DoctorHospital.is_active == True
        )

    doctors = query.distinct().all()

    # Filter language if requested
    if language:
        doctors = [
            d for d in doctors
            if any(language.lower() in lang.lower() for lang in d.languages_spoken)
        ]

    return [_serialize_doctor(d) for d in doctors]

@router.get("/{doctor_id}", response_model=DoctorOut)
def get_doctor_profile(doctor_id: str, db: Session = Depends(get_db)):
    """Returns comprehensive doctor profile including verified ratings and hospital affiliations."""
    doc = db.query(Doctor).options(
        joinedload(Doctor.user),
        joinedload(Doctor.hospitals).joinedload(DoctorHospital.hospital),
        joinedload(Doctor.hospitals).joinedload(DoctorHospital.department)
    ).filter(Doctor.id == doctor_id).first()

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return _serialize_doctor(doc)

@router.post("", response_model=DoctorOut, status_code=status.HTTP_201_CREATED)
def create_doctor_profile(
    payload: DoctorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a doctor profile (Doctor themselves or Admin)."""
    if current_user.role not in ["doctor", "super_admin", "hospital_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    
    target_user_id = payload.user_id if current_user.role in ["super_admin", "hospital_admin"] else current_user.id
    existing = db.query(Doctor).filter(Doctor.user_id == target_user_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor profile already exists for this user")

    doc = Doctor(
        user_id=target_user_id,
        license_number=payload.license_number,
        specialty=payload.specialty,
        experience_years=payload.experience_years,
        qualification=payload.qualification,
        bio=payload.bio,
        languages_spoken=payload.languages_spoken,
        gender=payload.gender,
        default_consultation_fee=payload.default_consultation_fee,
        is_verified=False
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    log_audit(db, current_user.id, "CREATE", "doctor", doc.id)
    return get_doctor_profile(doc.id, db)

@router.post("/{doctor_id}/verify", response_model=DoctorOut)
def verify_doctor(
    doctor_id: str,
    current_user: User = Depends(require_roles(["super_admin"])),
    db: Session = Depends(get_db)
):
    """Verifies doctor profile credentials (Super Admin only)."""
    doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    doc.is_verified = True
    db.commit()
    db.refresh(doc)
    log_audit(db, current_user.id, "VERIFY_DOCTOR", "doctor", doc.id)
    return get_doctor_profile(doc.id, db)

@router.post("/{doctor_id}/affiliations", response_model=DoctorHospitalOut, status_code=status.HTTP_201_CREATED)
def link_doctor_to_hospital(
    doctor_id: str,
    payload: DoctorHospitalLink,
    current_user: User = Depends(require_roles(["super_admin", "hospital_admin"])),
    db: Session = Depends(get_db)
):
    """Links a doctor to a hospital schedule. Hospital admins can only link to their own hospital."""
    verify_hospital_access(payload.hospital_id, current_user)
    
    existing = db.query(DoctorHospital).filter(
        DoctorHospital.doctor_id == doctor_id,
        DoctorHospital.hospital_id == payload.hospital_id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor is already affiliated with this hospital.")

    aff = DoctorHospital(
        doctor_id=doctor_id,
        hospital_id=payload.hospital_id,
        department_id=payload.department_id,
        consultation_fee=payload.consultation_fee,
        room_number=payload.room_number,
        is_primary=payload.is_primary,
        is_active=True
    )
    db.add(aff)
    db.commit()
    db.refresh(aff)
    log_audit(db, current_user.id, "LINK_DOCTOR_HOSPITAL", "doctor_hospital", aff.id, payload.hospital_id)
    
    hosp = db.query(Hospital).filter(Hospital.id == payload.hospital_id).first()
    dept = db.query(Department).filter(Department.id == payload.department_id).first() if payload.department_id else None

    return DoctorHospitalOut(
        id=aff.id,
        doctor_id=aff.doctor_id,
        hospital_id=aff.hospital_id,
        hospital_name=hosp.name if hosp else None,
        hospital_city=hosp.city if hosp else None,
        department_id=aff.department_id,
        department_name=dept.name if dept else None,
        consultation_fee=aff.consultation_fee,
        room_number=aff.room_number,
        is_primary=aff.is_primary,
        is_active=aff.is_active
    )
