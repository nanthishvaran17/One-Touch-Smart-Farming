from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.app.db.session import get_db
from backend.app.models.entities import Farm, User
from backend.app.schemas.schemas import FarmCreate, FarmOut
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/farms", tags=["Farms"])

@router.get("", response_model=List[FarmOut])
def get_farms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farms = db.query(Farm).filter(Farm.owner_id == current_user.id).all()
    return farms

@router.post("", response_model=FarmOut)
def create_farm(
    req: FarmCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = Farm(
        owner_id=current_user.id,
        name=req.name.strip(),
        location=req.location,
        latitude=req.latitude,
        longitude=req.longitude,
        timezone=req.timezone or "Asia/Kolkata",
        acreage=req.acreage or 5.0
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm

@router.get("/{farm_id}", response_model=FarmOut)
def get_farm(
    farm_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.owner_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found or access denied")
    return farm
