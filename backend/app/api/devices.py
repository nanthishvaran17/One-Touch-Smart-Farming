from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.app.db.session import get_db
from backend.app.models.entities import Device, Farm, User
from backend.app.api.deps import get_current_user
from backend.app.core.security import verify_password
from backend.app.services.hardware_simulator import hardware_simulator

router = APIRouter(prefix="/devices", tags=["Devices & Pairing"])

@router.get("")
def list_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    devices = db.query(Device).join(Farm).filter(Farm.owner_id == current_user.id).all()
    return [
        {
            "id": d.id,
            "serial_number": d.serial_number,
            "device_name": d.device_name,
            "is_paired": d.is_paired,
            "farm_id": d.farm_id,
            "status": d.status,
            "firmware_version": d.firmware_version,
            "last_heartbeat": d.last_heartbeat.isoformat() if d.last_heartbeat else None
        }
        for d in devices
    ]

@router.post("/pair")
def pair_device(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    serial = payload.get("serial_number", "").strip()
    token = payload.get("pairing_token", "").strip()
    farm_id = payload.get("farm_id")

    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.owner_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found or access denied")

    device = db.query(Device).filter(Device.serial_number == serial).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device with this serial number was not found in manufacturer registry.")

    if device.is_paired and device.farm_id != farm.id:
        raise HTTPException(status_code=400, detail="This controller is already paired to another farm. Ownership transfer requires authorization.")

    # Verify pairing token
    if not verify_password(token, device.pairing_token_hash):
        raise HTTPException(status_code=401, detail="Invalid device pairing token. Check label on controller.")

    device.is_paired = True
    device.farm_id = farm.id
    device.last_heartbeat = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "success",
        "message": f"Controller {device.serial_number} paired successfully with {farm.name}."
    }

@router.post("/simulator/toggle")
def toggle_simulator(payload: dict):
    enable = payload.get("enable", True)
    if enable:
        hardware_simulator.start()
        return {"status": "success", "simulator_running": True}
    else:
        hardware_simulator.stop()
        return {"status": "success", "simulator_running": False}

@router.post("/simulator/inject-fault")
def inject_simulator_fault(payload: dict):
    fault = payload.get("fault_type")  # None, 'UNDER_VOLTAGE', 'OVERLOAD', 'DRY_RUN', 'OBSTRUCTION'
    hardware_simulator.inject_fault(fault)
    return {"status": "success", "injected_fault": fault}
