# MediSlot: Master System Evaluation & Benchmark Report

**Generated:** 2026-10-14 14:03:17 UTC  
**Platform Location:** `D:\medislot`  
**Dataset:** 13,999 Historical Outpatient Consultations Across 40 Doctors & 4 Multi-Specialty Hospitals (Coimbatore, Erode, Tiruppur, Dharapuram)

---

## 1. Executive Summary

| Evaluation Domain | Target Criteria | Measured Benchmark | Status |
| :--- | :---: | :---: | :---: |
| **No-Show Prediction ROC-AUC** | $\ge 0.70$ | **0.7034** | **PASSED** |
| **No-Show Recall at Alert Threshold (0.35)** | $\ge 60.0\%$ | **64.8%** | **PASSED** |
| **Wait-Time MAE Error Reduction** | $\ge 25.0\%$ over naive | **39.3%** (MAE: 2.24m vs 3.68m) | **PASSED** |
| **Red-Flag Clinical Emergency Recall** | **100.0%** | **100.0%** (23/23 cases) | **PASSED** |
| **Natural Language Search Entity Extraction** | $\ge 90.0\%$ | **100.0%** (6/6 queries) | **PASSED** |
| **Inference Latency (ML & Duration)** | $< 20.0\text{ms}$ | **6.08 ms** (p95: 5.73 ms) | **PASSED** |
| **Multi-Factor Scoring Sanity** | $0.0 \le \text{Score} \le 1.0$ | **Bounded & Descending Order Confirmed** | **PASSED** |

---

## 2. Machine Learning Models Evaluation

### 2.1 Outpatient No-Show Prediction
- **Model Architecture:** Gradient Boosting Classifier (Champion) vs. Logistic Regression (Baseline).
- **ROC-AUC Score:** `0.7034` (PR-AUC: `0.5569`)
- **F1 Score:** `0.5678`
- **Clinical Intervention Threshold:** At threshold `0.35`, the model captures **64.8% of impending no-shows**, triggering high-urgency SMS/Email confirmation links 24h prior.
- **Top Predictive Features:**
  1. `past_no_show_rate` (42.0% feature importance)
  2. `lead_time_days` (14.6%)
  3. `appointment_type` (8.8%)
  4. `patient_age` (7.8%)
  5. `past_appointments` (5.8%)

### 2.2 Consultation Duration & Wait Time Regression
- **Model Architecture:** Gradient Boosting Regressor vs. Naive Baseline (Static Template duration: 20 mins).
- **Baseline Naive MAE:** `3.68 minutes`
- **Trained Model MAE:** `2.24 minutes`
- **Error Reduction:** **39.3% reduction in waiting-time prediction error**, exceeding the 25% target requirement.
- **Variance Explained ($R^2$):** `0.6931`

---

## 3. Clinical Safety & Red-Flag Triage Evaluation

- **Total Emergency Scenarios Tested:** `23`
- **Life Threats Correctly Intercepted:** `23`
- **Emergency Safety Recall:** **100.0% (Zero False Negatives on Acute Emergencies)**
- **Clinical Interception Action:** All routine outpatient booking mechanisms are completely disabled. Prompts immediate connection to:
  - **108** - Free Emergency Medical Ambulance Service (Tamil Nadu & National)
  - **112** - National Unified Emergency Service
  - Nearest Hospital Emergency Room directions

---

## 4. Multi-Factor Doctor Recommendation Sanity Check

- **Doctors Scored:** `4`
- **Score Bounding ($0.0 - 1.0$):** `Valid`
- **Descending Order Guarantee:** `Verified`
- **Top Scored Doctor ID:** `c1c91fc4-51e5-46da-b74a-51c61ecaf842` (Score: `0.776`)
- **Bayesian Prior Weighting:** Neutral prior of $\mu = 4.0$ with weight $m = 5$ prevents low-sample distortion while rewarding seasoned doctors with high review counts.

---

## 5. Performance & Latency Telemetry

- **Inference Sample Iterations:** `50`
- **Mean Latency:** `6.08 ms`
- **Median (p50) Latency:** `5.04 ms`
- **95th Percentile (p95) Latency:** `5.73 ms`
- **99th Percentile (p99) Latency:** `31.96 ms`
- **Performance Verdict:** Well below the `< 20ms` real-time budget, ensuring instant page rendering without blocking API workers.
