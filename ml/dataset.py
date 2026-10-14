import os
import sys
from datetime import datetime, date, timezone
from typing import Tuple, Dict, Any
import numpy as np
import pandas as pd
from sqlalchemy import text

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.database import SessionLocal
from app.services.availability import IST_ZONE

def extract_raw_outpatient_data() -> pd.DataFrame:
    """
    Extracts all appointment records with patient, doctor, and slot details from PostgreSQL.
    """
    db = SessionLocal()
    try:
        query = text("""
            SELECT 
                a.id AS appointment_id,
                a.patient_id,
                a.doctor_id,
                a.hospital_id,
                a.appointment_type,
                a.status,
                a.actual_duration_minutes,
                a.estimated_duration_minutes,
                a.estimated_wait_minutes,
                a.created_at AS booking_created_at,
                s.slot_start,
                s.slot_end,
                p.date_of_birth,
                p.gender AS patient_gender,
                d.specialty AS doctor_specialty,
                d.experience_years AS doctor_experience_years,
                d.default_consultation_fee AS consultation_fee,
                h.city AS hospital_city
            FROM appointments a
            JOIN slots s ON a.slot_id = s.id
            JOIN patients p ON a.patient_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            JOIN hospitals h ON a.hospital_id = h.id
            ORDER BY a.patient_id, s.slot_start ASC
        """)
        
        result = db.execute(query)
        rows = result.fetchall()
        columns = result.keys()
        
        df = pd.DataFrame(rows, columns=columns)
        return df
    finally:
        db.close()

def build_feature_engineered_dataset() -> pd.DataFrame:
    """
    Engineers temporal, patient behavioral, and clinical features with zero future data leakage.
    """
    df = extract_raw_outpatient_data()
    if df.empty:
        raise ValueError("No appointment records found in database. Run simulate_history.py first.")

    # 1. Temporal conversion
    df["slot_start_ist"] = pd.to_datetime(df["slot_start"]).dt.tz_convert(IST_ZONE)
    df["booking_created_at_ist"] = pd.to_datetime(df["booking_created_at"]).dt.tz_convert(IST_ZONE)

    # Lead time in days
    df["lead_time_days"] = (df["slot_start_ist"] - df["booking_created_at_ist"]).dt.total_seconds() / 86400.0
    df["lead_time_days"] = df["lead_time_days"].clip(lower=0.0)

    # Day of week (0 = Monday, 6 = Sunday)
    df["day_of_week"] = df["slot_start_ist"].dt.weekday

    # Hour of day as float (e.g., 9.33 for 9:20 AM)
    df["hour_of_day"] = df["slot_start_ist"].dt.hour + (df["slot_start_ist"].dt.minute / 60.0)
    df["is_morning"] = (df["hour_of_day"] < 12.0).astype(int)

    # 2. Patient Demographics
    today = date.today()
    def compute_age(dob):
        if pd.isna(dob) or dob is None:
            return 38.0
        if isinstance(dob, str):
            dob = pd.to_datetime(dob).date()
        return float(today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)))

    df["patient_age"] = df["date_of_birth"].apply(compute_age)
    df["patient_gender"] = df["patient_gender"].fillna("Unknown")

    # 3. Patient Historical Behavioral Features (strictly prior to current appointment)
    df = df.sort_values(by=["patient_id", "slot_start"]).reset_index(drop=True)
    
    # Binary no-show flag
    df["is_no_show_int"] = (df["status"] == "no_show").astype(int)
    df["is_completed_int"] = (df["status"] == "completed").astype(int)
    df["is_cancelled_int"] = (df["status"] == "cancelled").astype(int)

    # Cumulative counts strictly prior to this row
    df["past_appointments"] = df.groupby("patient_id").cumcount()
    df["past_no_shows"] = df.groupby("patient_id")["is_no_show_int"].cumsum() - df["is_no_show_int"]
    df["past_cancellations"] = df.groupby("patient_id")["is_cancelled_int"].cumsum() - df["is_cancelled_int"]
    df["past_completions"] = df.groupby("patient_id")["is_completed_int"].cumsum() - df["is_completed_int"]

    df["past_no_show_rate"] = np.where(
        df["past_appointments"] > 0,
        df["past_no_shows"] / df["past_appointments"],
        0.0
    )

    # 4. Binary Target for No-Show: 1 if no-show, 0 if completed
    # (Exclude cancelled appointments from the active attendance classifier)
    df["target_no_show"] = np.where(df["status"] == "no_show", 1, np.where(df["status"] == "completed", 0, -1))

    return df

def get_no_show_train_test_data(test_size: float = 0.20, random_state: int = 42):
    """
    Returns train/test split for No-Show binary classification (completed vs no_show).
    """
    df = build_feature_engineered_dataset()
    # Filter to completed and no-show
    df_cls = df[df["target_no_show"].isin([0, 1])].copy()

    feature_cols = [
        "lead_time_days",
        "appointment_type",
        "day_of_week",
        "hour_of_day",
        "patient_age",
        "patient_gender",
        "past_appointments",
        "past_no_shows",
        "past_no_show_rate",
        "past_cancellations",
        "doctor_specialty",
        "doctor_experience_years",
        "consultation_fee"
    ]

    X = df_cls[feature_cols].copy()
    y = df_cls["target_no_show"].astype(int).values

    from sklearn.model_selection import train_test_split
    return train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)

def get_wait_time_train_test_data(test_size: float = 0.20, random_state: int = 42):
    """
    Returns train/test split for Consultation Duration regression (completed appointments).
    """
    df = build_feature_engineered_dataset()
    df_reg = df[(df["status"] == "completed") & (df["actual_duration_minutes"].notna())].copy()

    feature_cols = [
        "appointment_type",
        "day_of_week",
        "hour_of_day",
        "patient_age",
        "doctor_specialty",
        "doctor_experience_years",
        "estimated_duration_minutes"
    ]

    X = df_reg[feature_cols].copy()
    y = df_reg["actual_duration_minutes"].astype(float).values

    from sklearn.model_selection import train_test_split
    return train_test_split(X, y, test_size=test_size, random_state=random_state)
