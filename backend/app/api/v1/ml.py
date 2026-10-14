from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.ml import (
    NoShowPredictionRequest,
    NoShowPredictionResponse,
    DurationPredictionRequest,
    DurationPredictionResponse,
    MLModelInfoResponse
)
from app.services.ml_service import ml_service

router = APIRouter(prefix="/ml", tags=["Machine Learning Inference"])

@router.post("/predict-no-show", response_model=NoShowPredictionResponse)
def predict_no_show_risk(
    payload: NoShowPredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Predicts outpatient no-show probability and risk classification:
    - Can evaluate an existing appointment by providing `appointment_id`.
    - Can evaluate speculative parameters for prospective scheduling.
    - Classifies risk into 'low' (<0.25), 'medium' (0.25-0.45), 'high' (>=0.45).
    - Recommends clinic intervention actions (SMS reminders, waitlist standby).
    """
    return ml_service.predict_no_show(request=payload, db=db)

@router.post("/predict-duration", response_model=DurationPredictionResponse)
def predict_consultation_duration(
    payload: DurationPredictionRequest
):
    """
    Predicts expected clinical consultation duration in minutes:
    - Factors in clinical specialty, appointment type (new vs. follow-up), physician experience, and time of day.
    - Computes variance against scheduled template duration.
    """
    return ml_service.predict_duration(request=payload)

@router.get("/model-info", response_model=MLModelInfoResponse)
def get_ml_model_metadata():
    """
    Returns operational metadata, evaluation metrics (ROC-AUC, MAE, R2),
    training timestamp, and active feature sets for production ML pipelines.
    """
    return ml_service.get_model_info()
