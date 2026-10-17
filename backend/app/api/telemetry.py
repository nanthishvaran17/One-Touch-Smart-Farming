from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.app.db.session import get_db
from backend.app.models.entities import Telemetry, Motor, Device, User
from backend.app.api.deps import get_current_user
from backend.app.services.telemetry_service import process_incoming_telemetry

router = APIRouter(tags=["Telemetry"])

@router.get("/motors/{motor_id}/telemetry")
def get_motor_telemetry(
    motor_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    motor = db.query(Motor).filter(Motor.id == motor_id).first()
    if not motor or motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Motor not found or access denied")

    records = db.query(Telemetry).filter(
        Telemetry.motor_id == motor_id
    ).order_by(Telemetry.timestamp.desc()).limit(min(limit, 200)).all()

    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "voltage_r": r.voltage_r,
            "voltage_y": r.voltage_y,
            "voltage_b": r.voltage_b,
            "avg_voltage": round((r.voltage_r + r.voltage_y + r.voltage_b) / 3, 1) if r.voltage_r else None,
            "current_r": r.current_r,
            "current_y": r.current_y,
            "current_b": r.current_b,
            "avg_current": round((r.current_r + r.current_y + r.current_b) / 3, 1) if r.current_r else None,
            "frequency": r.frequency,
            "flow_rate_lpm": r.flow_rate_lpm,
            "active_pipeline": r.active_pipeline,
            "current_rotation": r.current_rotation,
            "active_power_kw": r.active_power_kw,
            "controller_temp_c": r.controller_temp_c,
            "signal_strength_dbm": r.signal_strength_dbm,
            "mains_healthy": r.mains_healthy
        }
        for r in records
    ]

@router.get("/motors/{motor_id}/telemetry/summary")
def get_motor_telemetry_summary(
    motor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    motor = db.query(Motor).filter(Motor.id == motor_id).first()
    if not motor or motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Motor not found or access denied")

    latest = db.query(Telemetry).filter(
        Telemetry.motor_id == motor_id
    ).order_by(Telemetry.timestamp.desc()).first()

    return {
        "motor_id": motor.id,
        "name": motor.name,
        "status": motor.status,
        "total_runtime_hours": round(motor.total_runtime_hours, 2),
        "latest_voltage": round((latest.voltage_r + latest.voltage_y + latest.voltage_b) / 3, 1) if (latest and latest.voltage_r) else 0.0,
        "latest_current": round((latest.current_r + latest.current_y + latest.current_b) / 3, 1) if (latest and latest.current_r) else 0.0,
        "latest_flow_lpm": latest.flow_rate_lpm if latest else 0.0,
        "controller_temp_c": latest.controller_temp_c if latest else 30.0,
        "signal_strength_dbm": latest.signal_strength_dbm if latest else -70,
        "last_update": latest.timestamp.isoformat() if latest else None
    }

@router.post("/devices/telemetry")
def ingest_device_telemetry(
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    try:
        telemetry = process_incoming_telemetry(db, payload)
        return {"status": "success", "telemetry_id": telemetry.id}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(ex)}")
