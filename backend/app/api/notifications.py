from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.app.db.session import get_db
from backend.app.models.entities import Notification, FaultEvent, Motor, User
from backend.app.api.deps import get_current_user

router = APIRouter(tags=["Notifications & Faults"])

@router.get("/notifications")
def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notifs = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()

    lang = current_user.preferred_language or "ta"

    return [
        {
            "id": n.id,
            "category": n.category,
            "title": n.title_ta if lang == "ta" else n.title_en,
            "title_en": n.title_en,
            "title_ta": n.title_ta,
            "message": n.message_ta if lang == "ta" else n.message_en,
            "message_en": n.message_en,
            "message_ta": n.message_ta,
            "severity": n.severity,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        }
        for n in notifs
    ]

@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    db.commit()
    return {"status": "success"}

@router.get("/faults")
def get_active_faults(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    faults = db.query(FaultEvent).join(Motor).filter(
        Motor.farm.has(owner_id=current_user.id),
        FaultEvent.is_active == True
    ).order_by(FaultEvent.started_at.desc()).all()

    lang = current_user.preferred_language or "ta"

    return [
        {
            "id": f.id,
            "motor_id": f.motor_id,
            "motor_name": f.motor.name if f.motor else "Unknown",
            "fault_code": f.fault_code,
            "fault_name": f.fault_name,
            "severity": f.severity,
            "started_at": f.started_at.isoformat(),
            "explanation": f.farmer_explanation_ta if lang == "ta" else f.farmer_explanation_en,
            "safe_action": f.safe_action_ta if lang == "ta" else f.safe_action_en,
            "explanation_en": f.farmer_explanation_en,
            "explanation_ta": f.farmer_explanation_ta,
            "safe_action_en": f.safe_action_en,
            "safe_action_ta": f.safe_action_ta
        }
        for f in faults
    ]

@router.post("/faults/{fault_id}/resolve")
def resolve_fault(
    fault_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fault = db.query(FaultEvent).join(Motor).filter(
        FaultEvent.id == fault_id,
        Motor.farm.has(owner_id=current_user.id)
    ).first()
    if not fault:
        raise HTTPException(status_code=404, detail="Fault event not found")

    fault.is_active = False
    fault.resolved_at = datetime.now(timezone.utc)

    # Check if motor has any other active faults, if not restore to STOPPED
    remaining = db.query(FaultEvent).filter(
        FaultEvent.motor_id == fault.motor_id,
        FaultEvent.is_active == True
    ).count()

    if remaining == 0 and fault.motor:
        fault.motor.status = "STOPPED"
        fault.motor.last_status_change = datetime.now(timezone.utc)

    db.commit()
    return {"status": "success", "message": "Fault marked resolved. Motor status restored to STOPPED."}
