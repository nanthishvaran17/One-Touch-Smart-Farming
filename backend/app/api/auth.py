from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from backend.app.db.session import get_db
from backend.app.models.entities import User, Farm, Device, Motor, MotorSafetyConfig, MotorPipeline, UserSession
from backend.app.schemas.schemas import UserRegister, UserLogin, TokenResponse, UserSettingsUpdate
from backend.app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
def register(req: UserRegister, db: Session = Depends(get_db)):
    # Check if phone already registered
    existing = db.query(User).filter(User.phone_number == req.phone_number.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A farmer account with this phone number already exists."
        )

    user = User(
        phone_number=req.phone_number.strip(),
        full_name=req.full_name.strip(),
        hashed_password=hash_password(req.password),
        preferred_language=req.preferred_language,
        role="farmer",
        ui_mode="easy"
    )
    db.add(user)
    db.flush()

    # Automatically initialize their first farm
    farm = Farm(
        owner_id=user.id,
        name=req.farm_name or f"{user.full_name}'s Farm",
        location=req.farm_location or "Tamil Nadu",
        timezone="Asia/Kolkata",
        acreage=5.0
    )
    db.add(farm)
    db.flush()

    # Create session tokens
    access_token = create_access_token(user.id, role=user.role)
    refresh_token = create_refresh_token(user.id)

    user_session = UserSession(
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(user_session)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "preferred_language": user.preferred_language,
            "role": user.role,
            "ui_mode": user.ui_mode,
            "farm_id": farm.id,
            "farm_name": farm.name
        }
    }

@router.post("/login", response_model=TokenResponse)
def login(req: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == req.phone_number.strip()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password. Check credentials and retry."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled."
        )

    access_token = create_access_token(user.id, role=user.role)
    refresh_token = create_refresh_token(user.id)

    primary_farm = user.farms[0] if user.farms else None

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "preferred_language": user.preferred_language,
            "role": user.role,
            "ui_mode": user.ui_mode,
            "farm_id": primary_farm.id if primary_farm else None,
            "farm_name": primary_farm.name if primary_farm else None
        }
    }

@router.get("/me")
def get_profile(current_user: User = Depends(get_current_user)):
    primary_farm = current_user.farms[0] if current_user.farms else None
    return {
        "id": current_user.id,
        "phone_number": current_user.phone_number,
        "full_name": current_user.full_name,
        "preferred_language": current_user.preferred_language,
        "role": current_user.role,
        "ui_mode": current_user.ui_mode,
        "farm_id": primary_farm.id if primary_farm else None,
        "farm_name": primary_farm.name if primary_farm else None
    }

@router.patch("/settings")
def update_settings(
    req: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if req.full_name is not None:
        current_user.full_name = req.full_name.strip()
    if req.preferred_language is not None:
        current_user.preferred_language = req.preferred_language
    if req.ui_mode is not None:
        current_user.ui_mode = req.ui_mode
    db.commit()
    return {
        "status": "success",
        "preferred_language": current_user.preferred_language,
        "ui_mode": current_user.ui_mode
    }
