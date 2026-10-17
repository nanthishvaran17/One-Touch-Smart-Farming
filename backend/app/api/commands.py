from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.entities import Motor, MotorCommand, User
from backend.app.schemas.schemas import CommandCreate
from backend.app.api.deps import get_current_user
from backend.app.services.device_service import device_manager

router = APIRouter(prefix="/motors", tags=["Commands"])

@router.post("/{motor_id}/commands")
async def send_motor_command(
    motor_id: str,
    req: CommandCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    motor = db.query(Motor).filter(Motor.id == motor_id).first()
    if not motor or motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Motor not found or unauthorized access.")

    # Validate command type
    valid_types = ["START", "STOP", "EMERGENCY_STOP", "ROTATE_PIPELINE"]
    cmd_type = req.command_type.upper()
    if cmd_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid command type. Must be one of: {valid_types}")

    # Check motor safety status before starting
    if cmd_type == "START" and motor.status == "FAULT":
        raise HTTPException(
            status_code=400,
            detail="Cannot start motor while in FAULT state. Please inspect the farm alerts and resolve the fault first."
        )

    try:
        command = await device_manager.dispatch_command(
            db=db,
            motor=motor,
            command_type=cmd_type,
            parameters=req.parameters or {},
            user_id=current_user.id
        )
        return {
            "status": "success",
            "command_id": command.id,
            "idempotency_key": command.idempotency_key,
            "command_type": command.command_type,
            "state": command.status,
            "motor_id": motor.id,
            "motor_name": motor.name
        }
    except ConnectionError as ce:
        raise HTTPException(status_code=503, detail=str(ce))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch command: {str(ex)}")

@router.get("/commands/{command_id}")
def get_command_status(
    command_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cmd = db.query(MotorCommand).filter(MotorCommand.id == command_id).first()
    if not cmd or cmd.motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Command not found or unauthorized access.")

    return {
        "command_id": cmd.id,
        "idempotency_key": cmd.idempotency_key,
        "command_type": cmd.command_type,
        "status": cmd.status,
        "parameters": cmd.parameters,
        "feedback_data": cmd.feedback_data,
        "failure_reason": cmd.failure_reason,
        "transport_ack_at": cmd.transport_ack_at.isoformat() if cmd.transport_ack_at else None,
        "physical_ack_at": cmd.physical_ack_at.isoformat() if cmd.physical_ack_at else None,
        "created_at": cmd.created_at.isoformat() if cmd.created_at else None
    }
