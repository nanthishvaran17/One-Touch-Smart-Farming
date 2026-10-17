from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.app.db.session import get_db
from backend.app.models.entities import Motor, Farm, Device, MotorSafetyConfig, MotorPipeline, User, Telemetry
from backend.app.schemas.schemas import MotorCreate, MotorUpdate, SafetyConfigUpdate
from backend.app.api.deps import get_current_user
from backend.app.services.device_service import device_manager

router = APIRouter(tags=["Motors"])

@router.get("/farms/{farm_id}/motors")
def get_farm_motors(
    farm_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.owner_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found or access denied")

    motors_data = []
    for m in farm.motors:
        device_online = device_manager.is_device_online(m.device) if m.device else False
        
        # Get latest telemetry
        latest_telem = db.query(Telemetry).filter(
            Telemetry.motor_id == m.id
        ).order_by(Telemetry.timestamp.desc()).first()

        # Get active pipeline info
        active_pipe = next((p for p in m.pipelines if p.status in ["FLOWING", "ROTATING"]), None)
        if not active_pipe and m.pipelines:
            active_pipe = m.pipelines[0]

        motors_data.append({
            "id": m.id,
            "farm_id": m.farm_id,
            "name": m.name,
            "motor_type": m.motor_type,
            "hp_rating": m.hp_rating,
            "relay_channel": m.relay_channel,
            "status": m.status,
            "last_status_change": m.last_status_change.isoformat() if m.last_status_change else None,
            "total_runtime_hours": round(m.total_runtime_hours, 2),
            "device": {
                "id": m.device.id if m.device else None,
                "serial_number": m.device.serial_number if m.device else None,
                "device_name": m.device.device_name if m.device else None,
                "is_online": device_online,
                "firmware_version": m.device.firmware_version if m.device else None,
                "last_heartbeat": m.device.last_heartbeat.isoformat() if (m.device and m.device.last_heartbeat) else None
            } if m.device else None,
            "safety_config": {
                "min_voltage": m.safety_config.min_voltage if m.safety_config else 180.0,
                "max_voltage": m.safety_config.max_voltage if m.safety_config else 265.0,
                "max_current": m.safety_config.max_current if m.safety_config else 22.5,
                "dry_run_current": m.safety_config.dry_run_current if m.safety_config else 7.0,
                "max_runtime_minutes": m.safety_config.max_runtime_minutes if m.safety_config else 360
            } if m.safety_config else None,
            "active_pipeline": {
                "pipeline_index": active_pipe.pipeline_index if active_pipe else 1,
                "name": active_pipe.name if active_pipe else "Pipeline 1",
                "target_rotations": active_pipe.target_rotations if active_pipe else 5,
                "actual_rotations": active_pipe.actual_rotations if active_pipe else 0,
                "status": active_pipe.status if active_pipe else "IDLE",
                "flow_rate_lpm": active_pipe.flow_rate_lpm if active_pipe else 0.0
            } if active_pipe else None,
            "latest_reading": {
                "timestamp": latest_telem.timestamp.isoformat() if latest_telem else None,
                "voltage_r": latest_telem.voltage_r if latest_telem else None,
                "voltage_y": latest_telem.voltage_y if latest_telem else None,
                "voltage_b": latest_telem.voltage_b if latest_telem else None,
                "current_r": latest_telem.current_r if latest_telem else None,
                "current_y": latest_telem.current_y if latest_telem else None,
                "current_b": latest_telem.current_b if latest_telem else None,
                "flow_rate_lpm": latest_telem.flow_rate_lpm if latest_telem else 0.0,
                "active_power_kw": latest_telem.active_power_kw if latest_telem else 0.0,
                "controller_temp_c": latest_telem.controller_temp_c if latest_telem else None,
                "mains_healthy": latest_telem.mains_healthy if latest_telem else True
            } if latest_telem else None
        })
    return motors_data

@router.post("/farms/{farm_id}/motors")
def create_motor(
    farm_id: str,
    req: MotorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.owner_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found or access denied")

    device = None
    if req.device_id:
        device = db.query(Device).filter(Device.id == req.device_id, Device.farm_id == farm.id).first()
        if not device:
            raise HTTPException(status_code=400, detail="Specified controller is not paired to this farm.")

    motor = Motor(
        farm_id=farm.id,
        device_id=device.id if device else None,
        name=req.name.strip(),
        motor_type=req.motor_type,
        hp_rating=req.hp_rating,
        relay_channel=req.relay_channel,
        status="STOPPED"
    )
    db.add(motor)
    db.flush()

    # Safety configuration
    safety = MotorSafetyConfig(
        motor_id=motor.id,
        min_voltage=req.min_voltage,
        max_voltage=req.max_voltage,
        max_current=req.max_current,
        dry_run_current=req.dry_run_current,
        max_runtime_minutes=req.max_runtime_minutes
    )
    db.add(safety)

    # Initialize 7 pipelines for this motor with 5 rotations requirement
    for i in range(1, 8):
        pipe = MotorPipeline(
            motor_id=motor.id,
            pipeline_index=i,
            name=f"Pipeline {i} ({motor.name})",
            target_rotations=5,
            actual_rotations=0,
            is_enabled=True,
            status="IDLE",
            last_verified_position=i
        )
        db.add(pipe)

    db.commit()
    db.refresh(motor)
    return {"status": "success", "motor_id": motor.id, "name": motor.name}

@router.get("/motors/{motor_id}")
def get_motor_details(
    motor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    motor = db.query(Motor).filter(Motor.id == motor_id).first()
    if not motor or motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Motor not found or access denied")

    device_online = device_manager.is_device_online(motor.device) if motor.device else False

    return {
        "id": motor.id,
        "name": motor.name,
        "motor_type": motor.motor_type,
        "hp_rating": motor.hp_rating,
        "status": motor.status,
        "total_runtime_hours": motor.total_runtime_hours,
        "device": {
            "id": motor.device.id if motor.device else None,
            "serial_number": motor.device.serial_number if motor.device else None,
            "is_online": device_online,
            "last_heartbeat": motor.device.last_heartbeat.isoformat() if (motor.device and motor.device.last_heartbeat) else None
        } if motor.device else None,
        "safety_config": {
            "min_voltage": motor.safety_config.min_voltage if motor.safety_config else 180,
            "max_voltage": motor.safety_config.max_voltage if motor.safety_config else 265,
            "max_current": motor.safety_config.max_current if motor.safety_config else 22.5,
            "dry_run_current": motor.safety_config.dry_run_current if motor.safety_config else 7.0,
            "max_runtime_minutes": motor.safety_config.max_runtime_minutes if motor.safety_config else 360
        } if motor.safety_config else None,
        "pipelines": [
            {
                "id": p.id,
                "pipeline_index": p.pipeline_index,
                "name": p.name,
                "target_rotations": p.target_rotations,
                "actual_rotations": p.actual_rotations,
                "is_enabled": p.is_enabled,
                "status": p.status,
                "flow_rate_lpm": p.flow_rate_lpm,
                "fault_reason": p.fault_reason
            }
            for p in motor.pipelines
        ]
    }
