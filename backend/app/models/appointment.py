import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    appointment_number = Column(String(30), unique=True, nullable=False)
    slot_id = Column(String(36), ForeignKey("slots.id", ondelete="RESTRICT"), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="RESTRICT"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)

    appointment_type = Column(String(20), default="new_patient", nullable=False)  # 'new_patient', 'follow_up'
    status = Column(String(30), default="booked", nullable=False, index=True)  # 'booked', 'checked_in', 'in_consultation', 'completed', 'cancelled', 'no_show'

    # Queue and Live Timing metrics (UTC)
    check_in_time = Column(DateTime(timezone=True), nullable=True)
    consultation_start_time = Column(DateTime(timezone=True), nullable=True)
    consultation_end_time = Column(DateTime(timezone=True), nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)
    estimated_duration_minutes = Column(Integer, default=20, nullable=False)
    estimated_wait_minutes = Column(Integer, nullable=True)
    queue_number = Column(Integer, nullable=True)

    # Telemedicine and Cancellation
    telemedicine_meeting_url = Column(String(500), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    slot = relationship("Slot", back_populates="appointment")
    doctor = relationship("Doctor", back_populates="appointments")
    hospital = relationship("Hospital", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")
    reminder_jobs = relationship("ReminderJob", back_populates="appointment", cascade="all, delete-orphan")
    rating = relationship("DoctorRating", back_populates="appointment", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_appointments_doctor_status", "doctor_id", "status"),
        Index("idx_appointments_hospital_status", "hospital_id", "status"),
        Index("idx_appointments_patient_created", "patient_id", "created_at"),
    )

class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    preferred_date = Column(Date, nullable=False, index=True)
    preferred_time_range = Column(String(20), default="any", nullable=False)  # 'morning', 'afternoon', 'evening', 'any'
    status = Column(String(20), default="waiting", nullable=False)  # 'waiting', 'offered', 'accepted', 'expired', 'cancelled'
    offered_slot_id = Column(String(36), ForeignKey("slots.id", ondelete="SET NULL"), nullable=True)
    offer_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="waitlist_entries")

class ReminderJob(Base):
    __tablename__ = "reminder_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    reminder_type = Column(String(30), nullable=False)  # 'booking_confirmation', 'reminder_24h', 'reminder_2h', 'high_risk_extra'
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(20), default="scheduled", nullable=False)  # 'scheduled', 'processing', 'completed', 'failed', 'cancelled'
    confirmation_token = Column(String(255), unique=True, nullable=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    is_responded = Column(Boolean, default=False, nullable=False)
    response_action = Column(String(20), nullable=True)  # 'confirmed', 'cancelled'
    execution_count = Column(Integer, default=0, nullable=False)
    last_executed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    appointment = relationship("Appointment", back_populates="reminder_jobs")

    __table_args__ = (
        UniqueConstraint("appointment_id", "reminder_type", name="uq_reminder_job"),
    )

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    notification_type = Column(String(50), nullable=False)
    channel = Column(String(20), default="email", nullable=False)  # 'email', 'sms', 'in_app'
    recipient = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # 'pending', 'sent', 'failed'
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

class DoctorRating(Base):
    __tablename__ = "doctor_ratings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5
    review_text = Column(Text, nullable=True)
    is_moderated = Column(Boolean, default=False, nullable=False)
    moderation_status = Column(String(20), default="pending", nullable=False)  # 'pending', 'approved', 'rejected'
    moderated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moderated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    appointment = relationship("Appointment", back_populates="rating")
    doctor = relationship("Doctor", back_populates="ratings")
    patient = relationship("Patient", back_populates="ratings")
