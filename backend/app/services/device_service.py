import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import uuid

from sqlalchemy.orm import Session
from backend.app.models.entities import Motor, Device, MotorCommand, MotorPipeline, AuditLog
from backend.app.core.config import settings

class DeviceManager:
    """
    Manages physical IoT controller connections, command queues, and acknowledgement lifecycles.
    """
    def __init__(self):
        # Maps device_id -> active websocket or connection handler
        self._active_connections: Dict[str, Any] = {}
        # Pending commands awaiting physical ACK
        self._pending_commands: Dict[str, asyncio.Future] = {}

    def register_connection(self, device_id: str, connection: Any):
        self._active_connections[device_id] = connection

    def unregister_connection(self, device_id: str):
        if device_id in self._active_connections:
            del self._active_connections[device_id]

    def is_device_online(self, device: Device) -> bool:
        if not device.last_heartbeat:
            return False
        now = datetime.now(timezone.utc)
        # Ensure device.last_heartbeat is timezone aware
        last_hb = device.last_heartbeat
        if last_hb.tzinfo is None:
            last_hb = last_hb.replace(tzinfo=timezone.utc)
        return (now - last_hb).total_seconds() < settings.DEVICE_OFFLINE_THRESHOLD_SECONDS

    async def dispatch_command(
        self,
        db: Session,
        motor: Motor,
        command_type: str,
        parameters: dict,
        user_id: Optional[str] = None
    ) -> MotorCommand:
        device = motor.device
        if not device:
            raise ValueError("Motor is not linked to any registered physical controller.")

        if not self.is_device_online(device):
            raise ConnectionError(
                f"Controller '{device.device_name}' is currently offline. "
                "For physical safety, remote commands cannot be dispatched. "
                "Please check controller power supply or use local emergency stop."
            )

        # Generate unique idempotency key
        idempotency_key = f"CMD-{motor.id[:8]}-{int(datetime.now(timezone.utc).timestamp())}-{uuid.uuid4().hex[:6]}"

        command = MotorCommand(
            motor_id=motor.id,
            device_id=device.id,
            user_id=user_id,
            idempotency_key=idempotency_key,
            command_type=command_type,
            parameters=parameters,
            status="QUEUED"
        )
        db.add(command)
        db.commit()
        db.refresh(command)

        # If device connection is actively listening, push packet
        packet = {
            "type": "MOTOR_COMMAND",
            "command_id": command.id,
            "idempotency_key": command.idempotency_key,
            "relay_channel": motor.relay_channel,
            "action": command_type,
            "parameters": parameters,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Update command status to SENT
        command.status = "SENT"
        db.commit()

        # Audit log
        audit = AuditLog(
            user_id=user_id,
            action=f"DISPATCH_{command_type}",
            resource_type="motor",
            resource_id=motor.id,
            payload={"command_id": command.id, "parameters": parameters}
        )
        db.add(audit)
        db.commit()

        return command

    def handle_command_ack(
        self,
        db: Session,
        command_id: str,
        ack_type: str,  # 'TRANSPORT' or 'PHYSICAL'
        status: str,    # 'ACKNOWLEDGED', 'EXECUTING', 'SUCCEEDED', 'REJECTED', 'FAILED'
        feedback_data: Optional[dict] = None,
        failure_reason: Optional[str] = None
    ) -> Optional[MotorCommand]:
        command = db.query(MotorCommand).filter(MotorCommand.id == command_id).first()
        if not command:
            return None

        now = datetime.now(timezone.utc)
        if ack_type == "TRANSPORT":
            command.transport_ack_at = now
            command.status = "ACKNOWLEDGED"
        elif ack_type == "PHYSICAL":
            command.physical_ack_at = now
            command.status = status
            if feedback_data:
                command.feedback_data = feedback_data
            if failure_reason:
                command.failure_reason = failure_reason

            # Update motor status based on confirmed physical feedback
            motor = command.motor
            if motor:
                if status == "SUCCEEDED":
                    if command.command_type == "START":
                        motor.status = "RUNNING"
                        motor.last_status_change = now
                    elif command.command_type in ["STOP", "EMERGENCY_STOP"]:
                        motor.status = "STOPPED"
                        motor.last_status_change = now
                elif status in ["FAILED", "REJECTED"]:
                    motor.status = "FAULT"
                    motor.last_status_change = now

        db.commit()
        db.refresh(command)
        return command

device_manager = DeviceManager()
