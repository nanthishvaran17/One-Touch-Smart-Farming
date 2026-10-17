from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.db.session import get_db
from backend.app.models.entities import Schedule, ScheduleExecution, Motor, User
from backend.app.schemas.schemas import ScheduleCreate, ScheduleUpdate
from backend.app.api.deps import get_current_user

router = APIRouter(tags=["Schedules"])

@router.get("/motors/{motor_id}/schedules")
def get_motor_schedules(
    motor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    motor = db.query(Motor).filter(Motor.id == motor_id).first()
    if not motor or motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Motor not found or access denied")

    schedules = db.query(Schedule).filter(Schedule.motor_id == motor_id).all()
    return [
        {
            "id": s.id,
            "motor_id": s.motor_id,
            "motor_name": motor.name,
            "name": s.name,
            "schedule_type": s.schedule_type,
            "days_of_week": s.days_of_week,
            "start_time": s.start_time,
            "stop_time": s.stop_time,
            "duration_minutes": s.duration_minutes,
            "pipeline_mode": s.pipeline_mode,
            "pipeline_sequence": s.pipeline_sequence,
            "is_active": s.is_active,
            "timezone": s.timezone,
            "created_at": s.created_at.isoformat()
        }
        for s in schedules
    ]

@router.post("/motors/{motor_id}/schedules")
def create_schedule(
    motor_id: str,
    req: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    motor = db.query(Motor).filter(Motor.id == motor_id).first()
    if not motor or motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Motor not found or access denied")

    # Validate time format "HH:MM"
    try:
        parts = req.start_time.split(":")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid start_time format. Must be HH:MM in 24hr format.")

    sched = Schedule(
        motor_id=motor.id,
        farm_id=motor.farm_id,
        name=req.name.strip(),
        schedule_type=req.schedule_type,
        days_of_week=req.days_of_week,
        start_time=req.start_time,
        stop_time=req.stop_time,
        duration_minutes=req.duration_minutes,
        pipeline_mode=req.pipeline_mode,
        pipeline_sequence=req.pipeline_sequence,
        is_active=req.is_active,
        timezone=req.timezone or motor.farm.timezone or "Asia/Kolkata"
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return {"status": "success", "schedule_id": sched.id, "name": sched.name}

@router.patch("/schedules/{schedule_id}")
def update_schedule(
    schedule_id: str,
    req: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sched = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not sched or sched.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Schedule not found or access denied")

    if req.name is not None:
        sched.name = req.name.strip()
    if req.days_of_week is not None:
        sched.days_of_week = req.days_of_week
    if req.start_time is not None:
        sched.start_time = req.start_time
    if req.stop_time is not None:
        sched.stop_time = req.stop_time
    if req.duration_minutes is not None:
        sched.duration_minutes = req.duration_minutes
    if req.pipeline_mode is not None:
        sched.pipeline_mode = req.pipeline_mode
    if req.is_active is not None:
        sched.is_active = req.is_active

    db.commit()
    return {"status": "success", "schedule_id": sched.id, "is_active": sched.is_active}

@router.delete("/schedules/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sched = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not sched or sched.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Schedule not found or access denied")

    db.delete(sched)
    db.commit()
    return {"status": "success", "message": "Schedule deleted"}

@router.get("/schedules/{schedule_id}/executions")
def get_schedule_executions(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sched = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not sched or sched.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Schedule not found or access denied")

    executions = db.query(ScheduleExecution).filter(
        ScheduleExecution.schedule_id == schedule_id
    ).order_by(ScheduleExecution.planned_start_time.desc()).limit(20).all()

    return [
        {
            "id": ex.id,
            "status": ex.status,
            "planned_start_time": ex.planned_start_time.isoformat(),
            "actual_start_time": ex.actual_start_time.isoformat() if ex.actual_start_time else None,
            "actual_end_time": ex.actual_end_time.isoformat() if ex.actual_end_time else None,
            "error_message": ex.error_message
        }
        for ex in executions
    ]
