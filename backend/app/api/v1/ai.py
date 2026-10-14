from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_current_user
from app.models.user import User
from app.schemas.ai import (
    TriageRequest,
    TriageResponse,
    NLSearchRequest,
    NLSearchResponse,
    AIChatRequest,
    AIChatResponse,
    AIQuotaStatus,
)
from app.services.ai_service import (
    triage_patient_symptoms,
    parse_natural_language_search,
    chat_with_assistant,
)
from app.services.llm_client import gemini_client

router = APIRouter(prefix="/ai", tags=["AI & Clinical Triage"])


@router.post("/triage", response_model=TriageResponse)
def triage_symptoms(
    req: TriageRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Two-step symptom triage:
    1. Deterministic Red-Flag evaluation (108/112 emergency routing, routine booking blocked).
    2. LLM or rule-based medical specialty mapping with clinical reasoning and clarifying questions.
    """
    user_id = current_user.id if current_user else None
    return triage_patient_symptoms(req=req, db=db, user_id=user_id)


@router.post("/parse-search", response_model=NLSearchResponse)
def parse_search_query(
    req: NLSearchRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Parses conversational queries into structured search filters (specialty, city, gender, language, fee, date)
    and queries the multi-factor doctor recommendation engine.
    """
    user_id = current_user.id if current_user else None
    return parse_natural_language_search(req=req, db=db, user_id=user_id)


@router.post("/chat", response_model=AIChatResponse)
def chat_assistant(
    req: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Conversational assistant for guided discovery, symptom exploration, and slot proposals.
    Strictly adheres to Human-in-the-Loop: returns a BookingProposal that requires patient confirmation.
    """
    user_id = current_user.id if current_user else None
    return chat_with_assistant(req=req, db=db, user_id=user_id)


@router.get("/quota", response_model=AIQuotaStatus)
def get_ai_service_quota():
    """
    Returns production status of the Gemini LLM service, model identifier, and daily quota utilization.
    """
    return gemini_client.get_quota_status()
