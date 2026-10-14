from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.hospitals import router as hospitals_router
from app.api.v1.doctors import router as doctors_router
from app.api.v1.patients import router as patients_router
from app.api.v1.slots import router as slots_router
from app.api.v1.appointments import router as appointments_router
from app.api.v1.waitlist import router as waitlist_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(hospitals_router)
api_router.include_router(doctors_router)
api_router.include_router(patients_router)
api_router.include_router(slots_router)
api_router.include_router(appointments_router)
api_router.include_router(waitlist_router)
