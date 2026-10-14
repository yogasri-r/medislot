import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Time, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class WeeklyAvailabilityTemplate(Base):
    __tablename__ = "weekly_availability_templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0 = Monday, 6 = Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    slot_duration_minutes = Column(Integer, default=20, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    doctor = relationship("Doctor", back_populates="weekly_templates")

    __table_args__ = (
        Index("idx_templates_doctor_day", "doctor_id", "day_of_week"),
    )

class DateSpecificException(Base):
    __tablename__ = "date_specific_exceptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=True)
    exception_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=True)  # None = full day blocked
    end_time = Column(Time, nullable=True)
    exception_type = Column(String(30), nullable=False)  # 'leave', 'holiday', 'blocked', 'custom_hours'
    reason = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    doctor = relationship("Doctor", back_populates="date_exceptions")

class Slot(Base):
    __tablename__ = "slots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_start = Column(DateTime(timezone=True), nullable=False, index=True)
    slot_end = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="available", nullable=False)  # 'available', 'booked', 'blocked'
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    doctor = relationship("Doctor", back_populates="slots")
    hospital = relationship("Hospital", back_populates="slots")
    appointment = relationship("Appointment", back_populates="slot", uselist=False)

    __table_args__ = (
        UniqueConstraint("doctor_id", "slot_start", name="uq_doctor_slot_start"),
        Index("idx_slots_search", "doctor_id", "hospital_id", "status", "slot_start"),
    )
