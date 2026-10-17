from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.app.db.session import get_db
from backend.app.models.entities import Motor, MotorPipeline, User
from backend.app.schemas.schemas import PipelineConfigUpdate
from backend.app.api.deps import get_current_user
from backend.app.services.pipeline_service import pipeline_service
from backend.app.services.device_service import device_manager

router = APIRouter(tags=["Pipelines"])

@router.get("/motors/{motor_id}/pipelines")
def get_pipelines(
    motor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    motor = db.query(Motor).filter(Motor.id == motor_id).first()
    if not motor or motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Motor not found or access denied")

    pipelines = pipeline_service.get_motor_pipelines(db, motor.id)
    return [
        {
            "id": p.id,
            "pipeline_index": p.pipeline_index,
            "name": p.name,
            "target_rotations": p.target_rotations,
            "actual_rotations": p.actual_rotations,
            "is_enabled": p.is_enabled,
            "status": p.status,
            "flow_rate_lpm": p.flow_rate_lpm,
            "last_verified_position": p.last_verified_position,
            "fault_reason": p.fault_reason
        }
        for p in pipelines
    ]

@router.patch("/pipelines/{pipeline_id}/configuration")
def update_pipeline_config(
    pipeline_id: str,
    req: PipelineConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pipe = db.query(MotorPipeline).filter(MotorPipeline.id == pipeline_id).first()
    if not pipe or pipe.motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Pipeline not found or access denied")

    if req.name is not None:
        pipe.name = req.name.strip()
    if req.target_rotations is not None:
        if req.target_rotations < 1 or req.target_rotations > 50:
            raise HTTPException(status_code=400, detail="Target rotations must be between 1 and 50.")
        pipe.target_rotations = req.target_rotations
    if req.is_enabled is not None:
        pipe.is_enabled = req.is_enabled

    db.commit()
    return {
        "status": "success",
        "pipeline_id": pipe.id,
        "pipeline_index": pipe.pipeline_index,
        "name": pipe.name,
        "target_rotations": pipe.target_rotations,
        "is_enabled": pipe.is_enabled
    }

@router.get("/motors/{motor_id}/pipeline-state")
def get_pipeline_state(
    motor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    motor = db.query(Motor).filter(Motor.id == motor_id).first()
    if not motor or motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Motor not found or access denied")

    pipelines = pipeline_service.get_motor_pipelines(db, motor.id)
    active_pipe = next((p for p in pipelines if p.status in ["FLOWING", "ROTATING"]), None)

    return {
        "motor_id": motor.id,
        "motor_name": motor.name,
        "motor_status": motor.status,
        "active_pipeline_index": active_pipe.pipeline_index if active_pipe else 1,
        "active_pipeline_name": active_pipe.name if active_pipe else "Pipeline 1",
        "actual_rotations": active_pipe.actual_rotations if active_pipe else 0,
        "target_rotations": active_pipe.target_rotations if active_pipe else 5,
        "total_pipelines": len(pipelines),
        "pipelines": [
            {
                "index": p.pipeline_index,
                "name": p.name,
                "rotations": f"{p.actual_rotations}/{p.target_rotations}",
                "status": p.status,
                "is_active": (active_pipe and active_pipe.id == p.id),
                "flow_lpm": p.flow_rate_lpm
            }
            for p in pipelines
        ]
    }

@router.post("/motors/{motor_id}/pipelines/reset")
def reset_pipeline_sequence(
    motor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    motor = db.query(Motor).filter(Motor.id == motor_id).first()
    if not motor or motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Motor not found or access denied")

    pipeline_service.reset_pipeline_sequence(db, motor.id, start_index=1)
    return {"status": "success", "message": "Pipeline rotation sequence reset to Line 1."}
