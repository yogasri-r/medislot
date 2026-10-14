from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles, verify_hospital_access, log_audit
from app.models.user import User
from app.models.hospital import Hospital, Department
from app.schemas.hospital import HospitalCreate, HospitalUpdate, HospitalOut, DepartmentCreate, DepartmentOut

router = APIRouter(prefix="/hospitals", tags=["Hospitals"])

@router.get("", response_model=List[HospitalOut])
def list_hospitals(city: Optional[str] = None, db: Session = Depends(get_db)):
    """Lists all active hospitals, optionally filtered by city."""
    query = db.query(Hospital).filter(Hospital.is_active == True)
    if city:
        query = query.filter(Hospital.city.ilike(f"%{city}%"))
    return query.order_by(Hospital.name).all()

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
