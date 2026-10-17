from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.entities import User, Motor
from backend.app.schemas.schemas import VoiceQueryRequest
from backend.app.api.deps import get_current_user
from backend.app.services.voice_assistant import voice_intent_engine
from backend.app.services.device_service import device_manager

router = APIRouter(prefix="/voice", tags=["Voice Assistant"])

@router.post("/query")
def process_voice_query(
    req: VoiceQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    lang = req.language or current_user.preferred_language or "ta"
    result = voice_intent_engine.process_utterance(
        db=db,
        farmer_id=current_user.id,
        text=req.text,
        language=lang
    )
    return result

@router.post("/execute-confirmed")
async def execute_confirmed_voice_action(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    motor_id = payload.get("motor_id")
    action = payload.get("action")  # START or STOP

    motor = db.query(Motor).filter(Motor.id == motor_id).first()
    if not motor or motor.farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Motor not found or unauthorized")

    lang = current_user.preferred_language or "ta"

    if action not in ["START", "STOP"]:
        raise HTTPException(status_code=400, detail="Unsupported voice action")

    try:
        command = await device_manager.dispatch_command(
            db=db,
            motor=motor,
            command_type=action,
            parameters={"source": "VOICE_ASSISTANT"},
            user_id=current_user.id
        )
        if action == "START":
            msg = f"{motor.name}-ஐ இயக்கும் கட்டளை அனுப்பப்பட்டது." if lang == "ta" else f"Start command sent to {motor.name}."
        else:
            msg = f"{motor.name}-ஐ நிறுத்தும் கட்டளை அனுப்பப்பட்டது." if lang == "ta" else f"Stop command sent to {motor.name}."

        return {
            "status": "success",
            "command_id": command.id,
            "response_text": msg
        }
    except Exception as ex:
        err_msg = f"கட்டளை அனுப்புவதில் தோல்வி: {str(ex)}" if lang == "ta" else f"Failed to dispatch: {str(ex)}"
        raise HTTPException(status_code=500, detail=err_msg)
