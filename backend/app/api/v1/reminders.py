from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.models.doctor import Doctor
from app.models.appointment import Notification
from app.schemas.reminder import (
    ReminderResponsePayload,
    ReminderResponseOut,
    DoctorDelayAlertPayload,
    NotificationOut
)
from app.services.reminder import (
    handle_reminder_response,
    process_pending_reminders,
    send_doctor_delay_alerts
)

router = APIRouter(prefix="/reminders", tags=["Reminders & Notifications"])

@router.get("/respond", response_model=ReminderResponseOut)
def respond_reminder_get(
    request: Request,
    token: str = Query(..., description="HMAC-SHA256 signed action token"),
    action: str = Query(..., pattern="^(confirmed|cancelled)$", description="Response action: 'confirmed' or 'cancelled'"),
    db: Session = Depends(get_db)
):
    """
    One-click confirmation or cancellation endpoint directly accessible from emails.
    Tamper-proof: verified by cryptographic HMAC signature and expiry.
    Returns branded HTML for browser clicks or JSON for API calls.
    """
    result = handle_reminder_response(token=token, action=action, db=db)

    # Check if request prefers HTML (browser click from email)
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        is_success = result["status"] in ["confirmed", "cancelled", "already_recorded"]
        badge_color = "#10b981" if result["status"] == "confirmed" else ("#ef4444" if result["status"] == "cancelled" else "#3b82f6")
        status_label = result["status"].replace("_", " ").upper()

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>MediSlot - Appointment Response</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }}
        .card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 40px;
            max-width: 480px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }}
        .logo {{
            font-size: 24px;
            font-weight: 700;
            color: #38bdf8;
            margin-bottom: 24px;
        }}
        .badge {{
            display: inline-block;
            background: {badge_color};
            color: #ffffff;
            font-weight: 600;
            font-size: 13px;
            padding: 6px 14px;
            border-radius: 9999px;
            letter-spacing: 0.05em;
            margin-bottom: 20px;
        }}
        h1 {{
            font-size: 20px;
            margin: 0 0 12px 0;
            color: #f1f5f9;
        }}
        p {{
            font-size: 15px;
            line-height: 1.6;
            color: #94a3b8;
            margin: 0 0 24px 0;
        }}
        .meta {{
            background: #0f172a;
            border-radius: 8px;
            padding: 12px;
            font-size: 13px;
            color: #cbd5e1;
            margin-bottom: 24px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">MediSlot</div>
        <div class="badge">{status_label}</div>
        <h1>{result["message"]}</h1>
        {f'<div class="meta">Appointment: <strong>{result.get("appointment_number", "")}</strong></div>' if result.get("appointment_number") else ''}
        <p>Your response helps our doctors prepare and allows waitlisted patients to access timely medical care.</p>
    </div>
</body>
</html>
        """
        return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)

    return ReminderResponseOut(**result)

@router.post("/respond", response_model=ReminderResponseOut)
def respond_reminder_post(
    payload: ReminderResponsePayload,
    db: Session = Depends(get_db)
):
    """
    JSON API for recording a patient's response to an appointment reminder.
    """
    result = handle_reminder_response(token=payload.token, action=payload.action, db=db)
    return ReminderResponseOut(**result)

@router.post("/trigger")
def trigger_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually triggers due reminder jobs immediately.
    Useful for testing and verification of worker idempotency.
    """
    count = process_pending_reminders(db)
    return {
        "status": "success",
        "processed_jobs_count": count,
        "message": f"Processed {count} pending reminder jobs."
    }

@router.post("/doctor-delay")
def trigger_doctor_delay(
    payload: DoctorDelayAlertPayload,
    current_user: User = Depends(require_roles(["doctor", "hospital_admin", "super_admin"])),
    db: Session = Depends(get_db)
):
    """
    Alerts all upcoming patients in the doctor's queue when a clinical delay occurs.
    Updates estimated wait times and advises adjusted arrival times.
    """
    # Permission check: Doctors can only trigger for themselves
    if current_user.role == "doctor":
        doc = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doc or doc.id != payload.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only broadcast delays for their own schedule."
            )

    # Permission check: Hospital admin can only trigger for their hospital
    if current_user.role == "hospital_admin":
        if current_user.hospital_id != payload.hospital_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hospital admins can only broadcast delays for their assigned hospital."
            )

    count = send_doctor_delay_alerts(
        doctor_id=payload.doctor_id,
        hospital_id=payload.hospital_id,
        delay_minutes=payload.delay_minutes,
        db=db
    )

    return {
        "status": "success",
        "alerted_patients_count": count,
        "delay_minutes": payload.delay_minutes,
        "message": f"Dispatched schedule delay alerts to {count} upcoming patients."
    }

@router.get("/notifications", response_model=List[NotificationOut])
def get_user_notifications(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns communications and notifications history for the authenticated user.
    """
    if current_user.role == "super_admin":
        notifications = db.query(Notification).order_by(Notification.created_at.desc()).limit(limit).all()
    else:
        notifications = db.query(Notification).filter(
            Notification.user_id == current_user.id
        ).order_by(Notification.created_at.desc()).limit(limit).all()

    return notifications
