# MediSlot: AI-Powered Multi-Hospital Appointment Scheduling & Queue Management

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.4+-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![Tests](https://img.shields.io/badge/Tests-51%20Passed-brightgreen?style=flat&logo=pytest&logoColor=white)](file:///d:/medislot/backend/tests)
[![License](https://img.shields.io/badge/License-Proprietary-blue.svg)](LICENSE)

> **Tagline:** *"Right doctor. Right slot. Less waiting."*

MediSlot is an enterprise-grade multi-hospital outpatient healthcare appointment scheduling, clinical queue optimization, and AI triage platform. Calibrated across Western Tamil Nadu healthcare clusters (Coimbatore, Erode, Tiruppur, Dharapuram), it synchronizes patient demand with physician availability to eliminate scheduling friction, minimize outpatient no-shows, and provide predictable waiting-time bounds.

---

## 1. System Architecture

```mermaid
graph TB
    subgraph Client ["Client Layer (Next.js 16 / React 19 / TS / Tailwind)"]
        Web[Responsive Web Portal]
        Chat[AI Assistant & Booking Widget]
        DoctorUI[Doctor Clinical Queue Dashboard]
        AdminUI[Hospital & Super Admin Governance]
    end

    subgraph API ["Backend Layer (FastAPI / Python 3.11)"]
        Gateway[FastAPI REST API & Middleware]
        AuthSvc[Auth & Hospital-Scoped RBAC]
        BookingSvc[Booking & Concurrency Engine]
        QueueSvc[Queue & Live Wait Estimator]
        RecSvc[Doctor & Smart Slot Recommender]
        MLSvc[ML Inference Service (Joblib)]
        AISvc[Gemini LLM Client + Red-Flag Triage]
        JobSvc[APScheduler Job Engine]
    end

    subgraph Storage ["Storage & Cache Layer (Docker Desktop)"]
        Postgres[(PostgreSQL 16 Relational DB)]
        Redis[(Redis 7 Cache & Rate Limiting)]
    end

    subgraph External ["External Services"]
        Gemini[Google Gemini API (gemini-2.5-flash)]
        SMTP[Console / SMTP Mailer]
    end

    Web --> Gateway
    Chat --> Gateway
    DoctorUI --> Gateway
    AdminUI --> Gateway

    Gateway --> AuthSvc
    Gateway --> BookingSvc
    Gateway --> QueueSvc
    Gateway --> RecSvc
    Gateway --> MLSvc
    Gateway --> AISvc

    BookingSvc --> Postgres
    AuthSvc --> Postgres
    QueueSvc --> Postgres
    QueueSvc --> Redis
    RecSvc --> Postgres
    JobSvc --> Postgres
    JobSvc --> SMTP
    AISvc --> Gemini
```

---

## 2. Core Technical Capabilities

### 🔐 Multi-Tenant Hospital-Scoped RBAC
- **Strict Tenancy at Query Layer**: Hospital Administrators can only view, manage, and modify records matching `hospital_id = current_user.hospital_id`.
- **4 Roles**: `patient`, `doctor`, `hospital_admin`, `super_admin`.
- **Cryptographic Security**: Argon2id password hashing, short-lived JWT access tokens (15m), and rotating refresh tokens (7d).

### ⚡ Concurrency-Safe Booking & Waitlist Engine
- **Transactional Row-Locking**: `SELECT ... FOR UPDATE` eliminates double-booking race conditions during high-concurrency bursts (verified with 20 parallel threads).
- **Automated Waitlist Offers**: When a booking is cancelled, the system automatically finds the top waitlisted patient and dispatches a time-limited booking offer (30-minute claim window).

### 📬 Automated Reminders & Signed One-Click Tokens
- **Idempotent Job Ledger**: Automated 24h and 2h appointment reminders that will never trigger duplicate messages upon worker retries.
- **Signed Expiring Action URLs**: HMAC-SHA256 tokens enable patients to confirm attendance or cancel with 1 click directly from notification emails.

### 🧠 Multi-Factor Recommendation & Smart Slots
- **Composite Scoring ($0.0 - 1.0$)**: Weighted evaluation combining specialty match (0.30), earliest slot (0.25), Bayesian rating shrinkage (0.20), Western Tamil Nadu cluster proximity (0.15), and experience (0.10).
- **Top 3 Suggested Slot Badges**: Highlights optimal slots with clinical reasoning (*"Optimal morning focus"*, *"Adjacent schedule gap-filling"*, *"Lowest expected delay creep"*).

### 📊 Machine Learning Models (< 10ms Inference Latency)
- **No-Show Classifier**: Gradient Boosting model trained on 13,999 appointments (`ROC-AUC: 0.7034`, `PR-AUC: 0.5569`). Clinical intervention threshold of `0.35` achieves **64.8% recall of impending no-shows**, triggering high-urgency confirmations.
- **Wait Time Regressor**: Gradient Boosting regression achieving **39.3% error reduction** over naive static templates (MAE: `2.24 mins` vs `3.68 mins`, $R^2 = 0.6931$).

### 🩺 Clinical AI & Emergency Guardrails (Gemini API)
- *Principle: The LLM interprets and explains; deterministic code decides and acts.*
- **Zero-Latency Red-Flag Triage**: 100% emergency recall on cardiac, stroke (FAST), respiratory distress, hemorrhage, anaphylaxis, and psychiatric crises. Routine booking is blocked, routing immediately to **108** (Ambulance) and **112** (National Emergency).
- **Natural Language Search Extractor**: Parses conversational queries into structured parameters.
- **Human-in-the-Loop Booking Assistant**: Generates structured `BookingProposal` cards requiring explicit user confirmation before any booking transaction is created.

---

## 3. Instant Demo Personas (Evaluator Quick-Start)

The application includes built-in 1-click demo persona buttons in the Navbar and Login page:

| Persona | Role | Email | Password | Scope & Primary Features |
| :--- | :--- | :--- | :--- | :--- |
| 👤 **Patient** | `patient` | `patient1@medislot.com` | `Patient@123456` | Search doctors, AI triage, book slots, live queue tracking |
| 🩺 **Doctor** | `doctor` | `doctor1@medislot.com` | `Doctor@123456` | Outpatient daily queue, check-in, start/finish visit, delay alerts |
| 🏥 **Hospital Admin** | `hospital_admin` | `admin.coimbatore@medislot.com` | `Hospital@123456` | Coimbatore Hospital operations, department analytics, doctor roster |
| 🛡️ **Super Admin** | `super_admin` | `admin@medislot.com` | `Admin@123456` | 4-Hospital network governance, doctor license verification, telemetry |

---

## 4. Setup & Installation Guide

### Prerequisites
- **Docker Desktop** (running with Linux containers)
- **Python 3.11+**
- **Node.js 18+** & `npm`

### Step 1: Start Infrastructure (PostgreSQL 16 & Redis 7)
```bash
# In project root (D:\medislot)
docker compose up -d

# Verify containers are healthy
docker compose ps
```

### Step 2: Backend Setup
```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed 4 hospitals, 40 doctors, 500 patients, and historical simulator data
cd ..
python scripts/seed_data.py
python scripts/simulate_history.py

# Launch FastAPI development server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API Documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- API Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### Step 3: Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Run Next.js development server
npm run dev
```
- Web Application: [http://localhost:3000](http://localhost:3000)

---

## 5. Master API Reference

| Method | Endpoint | Description | Access Scope |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Patient self-registration | Public |
| `POST` | `/api/v1/auth/login` | JWT OAuth2 authentication | Public |
| `GET` | `/api/v1/auth/me` | Current session user profile | Authenticated |
| `GET` | `/api/v1/hospitals` | List network hospitals | Public |
| `GET` | `/api/v1/hospitals/{id}/dashboard-stats`| Hospital operational statistics | Hospital Admin / Super Admin |
| `GET` | `/api/v1/hospitals/network-analytics` | Platform network telemetry | Super Admin |
| `GET` | `/api/v1/recommendations/doctors` | Multi-factor doctor recommendation | Public |
| `GET` | `/api/v1/recommendations/smart-slots` | Smart slot ranking & Top 3 badges | Public |
| `POST` | `/api/v1/appointments/book` | Concurrency row-locking booking | Patient |
| `GET` | `/api/v1/appointments/my` | Patient appointment history | Patient |
| `POST` | `/api/v1/appointments/{id}/cancel` | Cancel booking & trigger waitlist offer | Patient / Admin |
| `GET` | `/api/v1/queue/appointment/{id}` | Live queue position & wait estimate | Patient / Doctor / Admin |
| `GET` | `/api/v1/queue/doctor/{id}` | Doctor clinical outpatient queue | Doctor / Staff |
| `POST` | `/api/v1/reminders/doctor-delay` | Broadcast delay alerts to patients | Doctor / Staff |
| `POST` | `/api/v1/ai/triage` | Red-flag triage & specialty guidance | Public |
| `POST` | `/api/v1/ai/parse-search` | Natural language search query parsing | Public |
| `POST` | `/api/v1/ai/chat` | Conversational assistant & slot proposals| Public / Patient |
| `GET` | `/api/v1/ai/quota` | Gemini quota consumption & status | Public |
| `POST` | `/api/v1/ml/predict-no-show` | ML real-time no-show risk inference | Authenticated |
| `POST` | `/api/v1/ml/predict-duration` | ML consultation duration regression | Authenticated |

---

## 6. Verification & Test Suite

The platform includes **51 automated tests** covering unit, integration, concurrency, RBAC tenancy, ML inference, and AI safety:

```bash
# Run complete test suite against live PostgreSQL
cd backend
pytest tests/ -v
```

### Test Suite Breakdown:
- `test_ai_features.py` (18 tests): 100% emergency recall across 7 categories, routine specialty mapping, NL entity extraction, safe booking proposals, quota health.
- `test_auth_and_rbac.py` (8 tests): Argon2id hashing, token refresh, cross-hospital isolation (403 Forbidden checks).
- `test_booking_concurrency_and_lifecycle.py` (5 tests): Multi-threaded race condition prevention (20 threads), state machine validation, waitlist auto-offers.
- `test_ml_models_and_inference.py` (6 tests): Artifact integrity, latency benchmarks (< 20ms), risk stratification, reminder hook integration.
- `test_recommendations_and_queue.py` (7 tests): Scoring bounds, proximity matrix, smart slot suggestions, live queue wait-time intervals.
- `test_reminders_and_notifications.py` (7 tests): Worker idempotency, signed HMAC tokens, delay broadcasts.

---

## 7. Master System Benchmarks

Offline evaluation metrics generated by `evaluation/evaluate_all.py`:

```
================================================================================
Evaluation Domain                                Target          Measured Result
================================================================================
No-Show Prediction ROC-AUC                       >= 0.70         0.7034 (PASSED)
No-Show Recall at 0.35 Intervention Threshold    >= 60.0%        64.8%  (PASSED)
Wait-Time MAE Error Reduction Over Naive Rule    >= 25.0%        39.3%  (PASSED)
Red-Flag Clinical Emergency Recall               100.0%          100.0% (PASSED)
Natural Language Search Entity Extraction        >= 90.0%        100.0% (PASSED)
ML Inference Latency                             < 20.0 ms       6.08 ms (PASSED)
================================================================================
```
Complete report available in [evaluation/EVALUATION_REPORT.md](file:///d:/medislot/evaluation/EVALUATION_REPORT.md).

---

## 8. Synthetic Data & Clinical Safety Notice

- **Synthetic Data Disclaimer**: All hospital names, doctors, patients, appointment records, and consultation notes are generated synthetically for development, simulation, and evaluation. No real Protected Health Information (PHI) is used.
- **Clinical AI Disclaimer**: MediSlot's AI symptom guidance tool is designed strictly for outpatient specialty navigation and does not provide medical diagnoses. Patients experiencing severe symptoms, chest pain, or respiratory distress are guided immediately to dial 108/112 or visit an emergency room.
