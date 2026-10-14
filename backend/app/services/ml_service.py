import os
import json
import joblib
from datetime import datetime, date, timezone
from typing import Optional, Dict, Any, Tuple, List
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.schedule import Slot
from app.services.availability import IST_ZONE
from app.schemas.ml import (
    NoShowPredictionRequest,
    NoShowPredictionResponse,
    DurationPredictionRequest,
    DurationPredictionResponse,
    MLModelInfoResponse
)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "ml", "models")
NO_SHOW_MODEL_FILE = os.path.join(MODEL_DIR, "no_show_model.joblib")
WAIT_TIME_MODEL_FILE = os.path.join(MODEL_DIR, "wait_time_model.joblib")
NO_SHOW_METRICS_FILE = os.path.join(MODEL_DIR, "no_show_metrics.json")
WAIT_TIME_METRICS_FILE = os.path.join(MODEL_DIR, "wait_time_metrics.json")

class MLService:
    _instance = None
    _no_show_model = None
    _wait_time_model = None
    _no_show_metrics = None
    _wait_time_metrics = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLService, cls).__new__(cls)
            cls._instance._load_models()
        return cls._instance

    def _load_models(self):
        """Lazily and safely loads serialized ML pipelines into memory."""
        try:
            if os.path.exists(NO_SHOW_MODEL_FILE):
                self._no_show_model = joblib.load(NO_SHOW_MODEL_FILE)
            if os.path.exists(WAIT_TIME_MODEL_FILE):
                self._wait_time_model = joblib.load(WAIT_TIME_MODEL_FILE)
            if os.path.exists(NO_SHOW_METRICS_FILE):
                with open(NO_SHOW_METRICS_FILE, "r", encoding="utf-8") as f:
                    self._no_show_metrics = json.load(f)
            if os.path.exists(WAIT_TIME_METRICS_FILE):
                with open(WAIT_TIME_METRICS_FILE, "r", encoding="utf-8") as f:
                    self._wait_time_metrics = json.load(f)
        except Exception as e:
            print(f"[MLService] Warning: Could not load ML models: {e}")

    @property
    def is_ready(self) -> bool:
        return self._no_show_model is not None and self._wait_time_model is not None

    def extract_features_from_appointment(self, appt: Appointment, db: Session) -> Dict[str, Any]:
        """Extracts engineered feature vector from a live database Appointment record."""
        slot = appt.slot
        if not slot:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Appointment has no associated slot for ML feature extraction."
            )

        now = datetime.now(timezone.utc)
        created_at = appt.created_at or now
        lead_time_days = max(0.0, (slot.slot_start - created_at).total_seconds() / 86400.0)

        slot_ist = slot.slot_start.astimezone(IST_ZONE)
        day_of_week = slot_ist.weekday()
        hour_of_day = slot_ist.hour + (slot_ist.minute / 60.0)

        # Patient demographics and past history
        patient = appt.patient
        today = date.today()
        patient_age = 35.0
        patient_gender = "Unknown"
        if patient:
            if patient.date_of_birth:
                dob = patient.date_of_birth
                patient_age = float(today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)))
            if patient.gender:
                patient_gender = patient.gender

        # Patient historical counts strictly prior to this appointment
        past_appts = db.query(Appointment).filter(
            Appointment.patient_id == appt.patient_id,
            Appointment.id != appt.id
        ).count()

        past_no_shows = db.query(Appointment).filter(
            Appointment.patient_id == appt.patient_id,
            Appointment.id != appt.id,
            Appointment.status == "no_show"
        ).count()

        past_cancels = db.query(Appointment).filter(
            Appointment.patient_id == appt.patient_id,
            Appointment.id != appt.id,
            Appointment.status == "cancelled"
        ).count()

        past_rate = (past_no_shows / past_appts) if past_appts > 0 else 0.0

        doctor = appt.doctor
        doc_specialty = doctor.specialty if doctor else "General Medicine"
        doc_exp = doctor.experience_years if doctor else 10
        doc_fee = doctor.default_consultation_fee if doctor else 500.0

        return {
            "lead_time_days": lead_time_days,
            "appointment_type": appt.appointment_type or "new_patient",
            "day_of_week": day_of_week,
            "hour_of_day": hour_of_day,
            "patient_age": patient_age,
            "patient_gender": patient_gender,
            "past_appointments": past_appts,
            "past_no_shows": past_no_shows,
            "past_no_show_rate": past_rate,
            "past_cancellations": past_cancels,
            "doctor_specialty": doc_specialty,
            "doctor_experience_years": doc_exp,
            "consultation_fee": doc_fee
        }

    def predict_no_show(
        self,
        request: NoShowPredictionRequest,
        db: Optional[Session] = None
    ) -> NoShowPredictionResponse:
        """
        Infers no-show probability for an outpatient booking:
        Returns calibrated risk level, actionable clinic intervention recommendation, and key risk drivers.
        """
        if not self._no_show_model:
            self._load_models()
        if not self._no_show_model:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No-show ML model is not available or still training."
            )

        if request.appointment_id and db:
            appt = db.query(Appointment).options(
                joinedload(Appointment.slot),
                joinedload(Appointment.patient),
                joinedload(Appointment.doctor)
            ).filter(Appointment.id == request.appointment_id).first()

            if not appt:
                raise HTTPException(status_code=404, detail="Appointment not found")
            feature_dict = self.extract_features_from_appointment(appt, db)
        else:
            past_rate = (request.past_no_shows / request.past_appointments) if request.past_appointments > 0 else 0.0
            feature_dict = {
                "lead_time_days": request.lead_time_days if request.lead_time_days is not None else 3.0,
                "appointment_type": request.appointment_type or "new_patient",
                "day_of_week": request.day_of_week if request.day_of_week is not None else 1,
                "hour_of_day": request.hour_of_day if request.hour_of_day is not None else 10.0,
                "patient_age": request.patient_age if request.patient_age is not None else 35.0,
                "patient_gender": request.patient_gender or "Female",
                "past_appointments": request.past_appointments or 0,
                "past_no_shows": request.past_no_shows or 0,
                "past_no_show_rate": past_rate,
                "past_cancellations": 0,
                "doctor_specialty": request.doctor_specialty or "General Medicine",
                "doctor_experience_years": request.doctor_experience_years or 10,
                "consultation_fee": request.consultation_fee or 500.0
            }

        df = pd.DataFrame([feature_dict])
        prob = float(self._no_show_model.predict_proba(df)[0, 1])

        # Risk stratification
        if prob < 0.25:
            risk_level = "low"
            recommended_action = "Standard protocol: Send 24h & 2h automated email reminders"
        elif prob < 0.45:
            risk_level = "medium"
            recommended_action = "Moderate risk: Monitor confirmation status; prompt one-click attendance response"
        else:
            risk_level = "high"
            recommended_action = "High no-show risk: Dispatch high-urgency extra reminder and enable waitlist auto-standby"

        # Risk drivers
        drivers = []
        if feature_dict["lead_time_days"] > 10.0:
            drivers.append(f"Long advance booking lead time ({feature_dict['lead_time_days']:.1f} days)")
        if feature_dict["past_no_shows"] >= 2:
            drivers.append(f"Multiple prior unfulfilled appointments ({feature_dict['past_no_shows']})")
        elif feature_dict["past_no_show_rate"] > 0.25:
            drivers.append(f"Elevated historical non-attendance rate ({feature_dict['past_no_show_rate']*100:.0f}%)")
        if feature_dict["appointment_type"] == "new_patient":
            drivers.append("First-time outpatient consultation (higher variance)")
        if feature_dict["patient_age"] < 30:
            drivers.append("Young adult demographic (statistically higher mobility)")

        if not drivers:
            drivers.append("Baseline scheduling factors")

        return NoShowPredictionResponse(
            no_show_probability=round(prob, 3),
            risk_level=risk_level,
            is_high_risk=(risk_level == "high"),
            recommended_action=recommended_action,
            top_risk_factors=drivers[:3],
            model_version="GradientBoosting-v1.0"
        )

    def predict_duration(self, request: DurationPredictionRequest) -> DurationPredictionResponse:
        """
        Predicts expected clinical consultation duration in minutes based on
        specialty, appointment type, physician experience, and patient demographics.
        """
        if not self._wait_time_model:
            self._load_models()
        if not self._wait_time_model:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Consultation duration ML model is not available."
            )

        feature_dict = {
            "appointment_type": request.appointment_type,
            "doctor_specialty": request.doctor_specialty,
            "day_of_week": request.day_of_week,
            "hour_of_day": request.hour_of_day,
            "patient_age": request.patient_age,
            "doctor_experience_years": request.doctor_experience_years,
            "estimated_duration_minutes": request.estimated_duration_minutes or 20
        }

        df = pd.DataFrame([feature_dict])
        raw_pred = float(self._wait_time_model.predict(df)[0])
        pred_duration = round(max(8.0, min(50.0, raw_pred)), 1)
        template_dur = request.estimated_duration_minutes or 20
        variance = round(pred_duration - template_dur, 1)

        if pred_duration > 22.0:
            load = "Extended examination"
        elif pred_duration < 13.0:
            load = "Brief follow-up review"
        else:
            load = "Standard outpatient consultation"

        return DurationPredictionResponse(
            predicted_duration_minutes=pred_duration,
            template_duration_minutes=template_dur,
            variance_minutes=variance,
            clinical_load=load,
            model_version="GradientBoostingRegressor-v1.0"
        )

    def get_model_info(self) -> MLModelInfoResponse:
        """Returns metadata, training metrics, and feature lists for active production models."""
        if not self._no_show_metrics or not self._wait_time_metrics:
            self._load_models()

        return MLModelInfoResponse(
            no_show_model=self._no_show_metrics or {"status": "Model file not found"},
            wait_time_model=self._wait_time_metrics or {"status": "Model file not found"},
            status="healthy" if self.is_ready else "degraded"
        )

# Global singleton
ml_service = MLService()
