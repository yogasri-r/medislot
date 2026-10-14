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
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

backend_path = os.path.join(project_root, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from ml.dataset import get_wait_time_train_test_data

MODEL_DIR = os.path.join(backend_path, "app", "ml", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

def train_wait_time_models():
    print("=" * 60)
    print("MediSlot: Training Consultation Duration & Wait Time Regression Models")
    print("=" * 60)

    X_train, X_test, y_train, y_test = get_wait_time_train_test_data(test_size=0.20, random_state=42)
    print(f"Dataset split: {len(X_train)} train samples, {len(X_test)} test samples")
    print(f"Target duration: mean={np.mean(y_train):.1f} mins, std={np.std(y_train):.1f} mins, range={np.min(y_train):.0f}-{np.max(y_train):.0f} mins")

    categorical_features = ["appointment_type", "doctor_specialty"]
    numeric_features = [
        "day_of_week",
        "hour_of_day",
        "patient_age",
        "doctor_experience_years",
        "estimated_duration_minutes"
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        ]
    )

    # 1. Naive Heuristic Baseline (Fixed template duration / estimate)
    naive_preds = X_test["estimated_duration_minutes"].values
    naive_mae = mean_absolute_error(y_test, naive_preds)
    naive_rmse = np.sqrt(mean_squared_error(y_test, naive_preds))
    print(f"\nNaive Baseline (Template Estimation) -> MAE: {naive_mae:.2f} mins, RMSE: {naive_rmse:.2f} mins")

    # 2. Linear / Ridge Baseline
    print("\nTraining Linear/Ridge Regression...")
    ridge_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", Ridge(alpha=1.0))
    ])
    ridge_pipeline.fit(X_train, y_train)
    ridge_preds = ridge_pipeline.predict(X_test)
    ridge_mae = mean_absolute_error(y_test, ridge_preds)
    ridge_rmse = np.sqrt(mean_squared_error(y_test, ridge_preds))
    ridge_r2 = r2_score(y_test, ridge_preds)
    print(f"Ridge Regression -> MAE: {ridge_mae:.2f} mins, RMSE: {ridge_rmse:.2f} mins, R2: {ridge_r2:.4f}")

    # 3. Champion: Gradient Boosting Regressor
    print("\nTraining Champion: Gradient Boosting Regressor...")
    gb_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.06,
            max_depth=4,
            random_state=42
        ))
    ])
    gb_pipeline.fit(X_train, y_train)
    gb_preds = gb_pipeline.predict(X_test)
    gb_mae = mean_absolute_error(y_test, gb_preds)
    gb_rmse = np.sqrt(mean_squared_error(y_test, gb_preds))
    gb_r2 = r2_score(y_test, gb_preds)

    mae_improvement = ((naive_mae - gb_mae) / naive_mae) * 100
    print(f"Gradient Boosting Regressor -> MAE: {gb_mae:.2f} mins, RMSE: {gb_rmse:.2f} mins, R2: {gb_r2:.4f}")
    print(f"MAE Error Reduction vs. Naive Baseline: {mae_improvement:.1f}%")

    # Feature Importances
    ohe = gb_pipeline.named_steps["preprocessor"].named_transformers_["cat"]
    cat_names = ohe.get_feature_names_out(categorical_features).tolist()
    all_names = numeric_features + cat_names
    importances = gb_pipeline.named_steps["regressor"].feature_importances_
    
    feat_imp = sorted(zip(all_names, importances), key=lambda x: x[1], reverse=True)
    print("\nTop Predictors of Consultation Duration:")
    for name, imp in feat_imp[:6]:
        print(f"  - {name}: {imp*100:.2f}%")

    # Serialize champion pipeline & metadata
    champion_path = os.path.join(MODEL_DIR, "wait_time_model.joblib")
    joblib.dump(gb_pipeline, champion_path)
    print(f"\nSaved champion model to: {champion_path}")

    metrics = {
        "model_name": "GradientBoostingRegressor",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "features": {
            "numeric": numeric_features,
            "categorical": categorical_features
        },
        "metrics": {
            "mae_minutes": round(float(gb_mae), 2),
            "rmse_minutes": round(float(gb_rmse), 2),
            "r2_score": round(float(gb_r2), 4),
            "naive_baseline_mae": round(float(naive_mae), 2),
            "mae_improvement_percent": round(float(mae_improvement), 1)
        },
        "top_features": [{"feature": name, "importance": round(float(imp), 4)} for name, imp in feat_imp[:8]]
    }

    metrics_path = os.path.join(MODEL_DIR, "wait_time_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved evaluation metrics to: {metrics_path}")

    return metrics

if __name__ == "__main__":
    train_wait_time_models()
