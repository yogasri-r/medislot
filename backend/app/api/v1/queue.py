from typing import Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.appointment import Appointment
from app.schemas.queue import QueueStatusOut, DoctorDailyQueueOut
from app.services.availability import IST_ZONE
from app.services.queue import get_appointment_queue_status, get_doctor_daily_queue

router = APIRouter(prefix="/queue", tags=["Live Queue & Wait Time Estimation"])

@router.get("/appointment/{appointment_id}", response_model=QueueStatusOut)
def get_appointment_live_queue(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns live queue position and dynamic estimated wait time for an appointment.
    Accessible by:
    - The patient who booked the appointment
    - The attending doctor
    - Hospital administrators/staff for the hospital hosting the appointment
    - Super admins
    """
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Permission check
    if current_user.role == "patient":
        if not current_user.patient_profile or appt.patient_id != current_user.patient_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only view your own appointment queue status."
            )
    elif current_user.role == "doctor":
        if not current_user.doctor_profile or appt.doctor_id != current_user.doctor_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Doctors can only view appointments assigned to them."
            )
    elif current_user.role in ["hospital_admin", "staff"]:
        if str(appt.hospital_id) != str(current_user.hospital_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot view appointment queue from another hospital."
            )
    elif current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Insufficient privileges."
        )

    return get_appointment_queue_status(appointment_id=appointment_id, db=db)

@router.get("/doctor/{doctor_id}", response_model=DoctorDailyQueueOut)
def get_doctor_queue(
    doctor_id: str,
    hospital_id: str = Query(..., description="Hospital ID"),
    target_date: Optional[date] = Query(None, description="Date for queue view (defaults to today IST)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns clinical outpatient daily queue for a doctor at a given hospital.
    Confidential endpoint for doctors and hospital administrators/staff.
    """
    # Permission check: patients cannot view the entire clinic queue
    if current_user.role == "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinic daily queues are restricted to doctors and hospital staff."
        )

    if current_user.role == "doctor":
        if not current_user.doctor_profile or current_user.doctor_profile.id != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only view your own daily queue."
            )
    elif current_user.role in ["hospital_admin", "staff"]:
        if str(hospital_id) != str(current_user.hospital_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot view clinic queues for other hospitals."
            )
    elif current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Insufficient privileges."
        )

    if not target_date:
        target_date = datetime.now(IST_ZONE).date()

    return get_doctor_daily_queue(
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        target_date=target_date,
        db=db
    )
