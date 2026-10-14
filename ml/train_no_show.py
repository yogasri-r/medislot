import os
import sys
import json
import joblib
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    confusion_matrix,
    classification_report
)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

backend_path = os.path.join(project_root, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from ml.dataset import get_no_show_train_test_data

MODEL_DIR = os.path.join(backend_path, "app", "ml", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

def train_no_show_models():
    print("=" * 60)
    print("MediSlot: Training Outpatient No-Show Prediction Models")
    print("=" * 60)

    X_train, X_test, y_train, y_test = get_no_show_train_test_data(test_size=0.20, random_state=42)
    print(f"Dataset split: {len(X_train)} train samples, {len(X_test)} test samples")
    print(f"Class distribution: {np.mean(y_train)*100:.1f}% no-show in train, {np.mean(y_test)*100:.1f}% in test")

    categorical_features = ["appointment_type", "patient_gender", "doctor_specialty"]
    numeric_features = [
        "lead_time_days",
        "day_of_week",
        "hour_of_day",
        "patient_age",
        "past_appointments",
        "past_no_shows",
        "past_no_show_rate",
        "past_cancellations",
        "doctor_experience_years",
        "consultation_fee"
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        ]
    )

    # 1. Baseline: Logistic Regression
    print("\nTraining Baseline: Logistic Regression...")
    lr_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced"))
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_probs = lr_pipeline.predict_proba(X_test)[:, 1]
    lr_preds = (lr_probs >= 0.50).astype(int)

    lr_auc = roc_auc_score(y_test, lr_probs)
    lr_prec = precision_score(y_test, lr_preds, zero_division=0)
    lr_rec = recall_score(y_test, lr_preds, zero_division=0)
    lr_f1 = f1_score(y_test, lr_preds, zero_division=0)
    print(f"Logistic Regression -> ROC-AUC: {lr_auc:.4f}, Precision: {lr_prec:.4f}, Recall: {lr_rec:.4f}, F1: {lr_f1:.4f}")

    # 2. Champion: Gradient Boosting Classifier
    print("\nTraining Champion: Gradient Boosting Classifier...")
    gb_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", GradientBoostingClassifier(
            n_estimators=120,
            learning_rate=0.08,
            max_depth=4,
            random_state=42
        ))
    ])
    gb_pipeline.fit(X_train, y_train)
    gb_probs = gb_pipeline.predict_proba(X_test)[:, 1]
    
    # Evaluate at standard 0.50 threshold and clinical intervention 0.35 threshold
    gb_preds = (gb_probs >= 0.50).astype(int)
    gb_preds_intervention = (gb_probs >= 0.35).astype(int)

    gb_auc = roc_auc_score(y_test, gb_probs)
    gb_pr_auc = average_precision_score(y_test, gb_probs)
    gb_prec = precision_score(y_test, gb_preds, zero_division=0)
    gb_rec = recall_score(y_test, gb_preds, zero_division=0)
    gb_f1 = f1_score(y_test, gb_preds, zero_division=0)
    cm = confusion_matrix(y_test, gb_preds)

    print(f"Gradient Boosting   -> ROC-AUC: {gb_auc:.4f}, PR-AUC: {gb_pr_auc:.4f}, Precision: {gb_prec:.4f}, Recall: {gb_rec:.4f}, F1: {gb_f1:.4f}")
    print(f"Confusion Matrix (threshold=0.50):\nTN={cm[0,0]}  FP={cm[0,1]}\nFN={cm[1,0]}  TP={cm[1,1]}")

    rec_intervention = recall_score(y_test, gb_preds_intervention, zero_division=0)
    prec_intervention = precision_score(y_test, gb_preds_intervention, zero_division=0)
    print(f"Clinical Alert Mode (threshold=0.35) -> Recall: {rec_intervention:.4f}, Precision: {prec_intervention:.4f}")

    # Feature Importance Analysis
    ohe = gb_pipeline.named_steps["preprocessor"].named_transformers_["cat"]
    cat_feature_names = ohe.get_feature_names_out(categorical_features).tolist()
    all_feature_names = numeric_features + cat_feature_names
    importances = gb_pipeline.named_steps["classifier"].feature_importances_
    
    feat_imp = sorted(zip(all_feature_names, importances), key=lambda x: x[1], reverse=True)
    print("\nTop 8 Most Predictive Features:")
    for name, imp in feat_imp[:8]:
        print(f"  - {name}: {imp*100:.2f}%")

    # Serialize champion pipeline & metadata
    champion_path = os.path.join(MODEL_DIR, "no_show_model.joblib")
    joblib.dump(gb_pipeline, champion_path)
    print(f"\nSaved champion model to: {champion_path}")

    metrics = {
        "model_name": "GradientBoostingClassifier",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "features": {
            "numeric": numeric_features,
            "categorical": categorical_features
        },
        "metrics": {
            "roc_auc": round(float(gb_auc), 4),
            "pr_auc": round(float(gb_pr_auc), 4),
            "precision": round(float(gb_prec), 4),
            "recall": round(float(gb_rec), 4),
            "f1_score": round(float(gb_f1), 4),
            "intervention_recall_threshold_0_35": round(float(rec_intervention), 4),
            "intervention_precision_threshold_0_35": round(float(prec_intervention), 4),
            "confusion_matrix": {
                "tn": int(cm[0,0]),
                "fp": int(cm[0,1]),
                "fn": int(cm[1,0]),
                "tp": int(cm[1,1])
            }
        },
        "baseline_comparison": {
            "logistic_regression_roc_auc": round(float(lr_auc), 4),
            "logistic_regression_f1": round(float(lr_f1), 4),
            "roc_auc_lift": round(float(gb_auc - lr_auc), 4)
        },
        "top_features": [{"feature": name, "importance": round(float(imp), 4)} for name, imp in feat_imp[:10]]
    }

    metrics_path = os.path.join(MODEL_DIR, "no_show_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved evaluation metrics to: {metrics_path}")

    return metrics

if __name__ == "__main__":
    train_no_show_models()
