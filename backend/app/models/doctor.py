import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    license_number = Column(String(100), unique=True, nullable=False)
    specialty = Column(String(100), nullable=False, index=True)
    experience_years = Column(Integer, default=0, nullable=False)
    qualification = Column(String(200), nullable=False)
    bio = Column(Text, nullable=True)
    languages_spoken = Column(JSON_TYPE, default=list, nullable=False)  # e.g. ["English", "Tamil"]
    gender = Column(String(20), nullable=False)  # 'male', 'female', 'other'
    default_consultation_fee = Column(Float, default=500.0, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    rating_avg = Column(Float, default=4.0, nullable=False)  # Neutral prior for cold start
    rating_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="doctor_profile")
    hospitals = relationship("DoctorHospital", back_populates="doctor", cascade="all, delete-orphan")
    weekly_templates = relationship("WeeklyAvailabilityTemplate", back_populates="doctor", cascade="all, delete-orphan")
    date_exceptions = relationship("DateSpecificException", back_populates="doctor", cascade="all, delete-orphan")
    slots = relationship("Slot", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")
    ratings = relationship("DoctorRating", back_populates="doctor")

class DoctorHospital(Base):
    __tablename__ = "doctor_hospitals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    consultation_fee = Column(Float, nullable=False, default=500.0)
    room_number = Column(String(50), nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    doctor = relationship("Doctor", back_populates="hospitals")
    hospital = relationship("Hospital", back_populates="doctor_affiliations")
    department = relationship("Department", back_populates="doctor_affiliations")

    __table_args__ = (
        UniqueConstraint("doctor_id", "hospital_id", name="uq_doctor_hospital"),
    )
