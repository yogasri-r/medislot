from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.dependencies import get_current_user, log_audit
from app.models.user import User, RefreshToken
from app.models.patient import Patient
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, RefreshTokenRequest, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Registers a new user and issues access/refresh tokens."""
    # Check if email exists
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )
    # Check if phone exists
    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this phone number already exists."
        )

    # For safety, super_admin cannot be registered via public endpoint
    if payload.role == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin accounts cannot be created via public registration."
        )

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
        hospital_id=payload.hospital_id,
        is_active=True,
        is_verified=True if payload.role == "patient" else False
    )
    db.add(user)
    db.flush()

    # If patient, create Patient profile
    if payload.role == "patient":
        from datetime import date
        dob = payload.date_of_birth or date(1990, 1, 1)
        patient = Patient(
            user_id=user.id,
            date_of_birth=dob,
            gender=payload.gender or "other",
            blood_group=payload.blood_group,
            preferred_language=payload.preferred_language or "English"
        )
        db.add(patient)

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        hospital_id=user.hospital_id
    )
    refresh_token = create_refresh_token(subject=user.id)

    # Store refresh token
    ref_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_password(refresh_token[:32]),  # hash prefix for revocation tracking
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(ref_record)
    db.commit()
    db.refresh(user)

    log_audit(db, user.id, "REGISTER", "user", user.id, user.hospital_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user)
    )

@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticates user and returns JWT token pair."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact support."
        )

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        hospital_id=user.hospital_id
    )
    refresh_token = create_refresh_token(subject=user.id)

    ref_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_password(refresh_token[:32]),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(ref_record)
    db.commit()
    db.refresh(user)

    log_audit(db, user.id, "LOGIN", "user", user.id, user.hospital_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user)
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Rotates refresh token and issues fresh access token."""
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")
        user_id = data.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or invalid.")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found or disabled.")

    # Issue new pair
    access_token = create_access_token(subject=user.id, role=user.role, hospital_id=user.hospital_id)
    new_refresh_token = create_refresh_token(subject=user.id)

    ref_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_password(new_refresh_token[:32]),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(ref_record)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user)
    )

@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns the profile of currently authenticated user."""
    return UserOut.model_validate(current_user)
