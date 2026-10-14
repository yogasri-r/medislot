import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(50), nullable=False)  # E.g. 'VIEW_APPOINTMENT', 'CREATE_APPOINTMENT', 'UPDATE_STATUS'
    resource_type = Column(String(50), nullable=False)  # 'appointment', 'patient', 'doctor', 'hospital'
    resource_id = Column(String(100), nullable=False)
    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(JSON_TYPE, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")

class AIInteractionLog(Base):
    __tablename__ = "ai_interaction_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String(100), nullable=True)
    feature_type = Column(String(50), nullable=False, index=True)  # 'symptom_triage', 'nl_search', 'booking_assistant'
    input_text_anonymized = Column(Text, nullable=False)
    red_flag_triggered = Column(Boolean, default=False, nullable=False)
    urgency_level = Column(String(30), nullable=True)  # 'routine', 'soon', 'emergency'
    extracted_entities = Column(JSON_TYPE, nullable=True)
    tools_called = Column(JSON_TYPE, nullable=True)
    raw_response_json = Column(JSON_TYPE, nullable=True)
    latency_ms = Column(Integer, nullable=False)
    status = Column(String(30), default="success", nullable=False)  # 'success', 'fallback', 'quota_exceeded', 'error'
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
