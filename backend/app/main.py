from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
import app.models  # Ensure all models are registered
from app.api.v1 import api_router
from app.core.scheduler import start_scheduler, stop_scheduler

# Initialize database schema
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start background scheduler
    start_scheduler()
    yield
    # Shutdown: stop scheduler gracefully
    stop_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="MediSlot: AI-Powered Multi-Hospital Appointment Scheduling Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "platform": settings.PROJECT_NAME,
        "single_hospital_mode": settings.SINGLE_HOSPITAL_MODE,
        "timezone": settings.DEFAULT_TIMEZONE
    }
