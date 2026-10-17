from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import Motor, MotorPipeline, FaultEvent, Notification

class PipelineStateMachine:
    """
    State machine for the 7-Pipeline Mechanical Rotary Distributor.
    Enforces sequential irrigation across enabled pipelines with 5 rotations per line.
    """
    def __init__(self):
        pass

    def get_motor_pipelines(self, db: Session, motor_id: str) -> List[MotorPipeline]:
        return db.query(MotorPipeline).filter(
            MotorPipeline.motor_id == motor_id
        ).order_by(MotorPipeline.pipeline_index.asc()).all()

    def process_rotation_feedback(
        self,
        db: Session,
        motor: Motor,
        reported_pipeline_idx: int,
        rotation_pulse_increment: int = 1,
        flow_rate_lpm: float = 40.0
    ) -> Dict[str, Any]:
        """
        Called when physical controller emits a rotation switch pulse event.
        Tracks 5 rotations per pipeline, and steps to the next line upon completion.
        """
        pipelines = self.get_motor_pipelines(db, motor.id)
        if not pipelines:
            return {"error": "No pipelines configured for this motor"}

        active_pipe = next((p for p in pipelines if p.pipeline_index == reported_pipeline_idx), None)
        if not active_pipe:
            return {"error": f"Invalid pipeline index {reported_pipeline_idx}"}

        # Update flow rate and position
        active_pipe.flow_rate_lpm = flow_rate_lpm
        active_pipe.last_verified_position = reported_pipeline_idx

        # Increment rotations
        active_pipe.actual_rotations += rotation_pulse_increment
        active_pipe.status = "ROTATING"

        transition_occurred = False
        next_pipeline_idx = None

        # Check if 5 rotations reached for this line
        if active_pipe.actual_rotations >= active_pipe.target_rotations:
            active_pipe.status = "COMPLETED"
            active_pipe.actual_rotations = active_pipe.target_rotations
            transition_occurred = True

            # Find next enabled pipeline in 1..7 sequence
            current_idx = active_pipe.pipeline_index
            enabled_pipes = [p for p in pipelines if p.is_enabled]
            next_pipes = [p for p in enabled_pipes if p.pipeline_index > current_idx]

            if next_pipes:
                next_pipe = next_pipes[0]
            else:
                # Wrap around or complete cycle
                next_pipe = enabled_pipes[0] if enabled_pipes else None

            if next_pipe:
                next_pipeline_idx = next_pipe.pipeline_index
                next_pipe.status = "FLOWING"
                next_pipe.actual_rotations = 0

                # Notify farmer of pipeline transition
                notif = Notification(
                    user_id=motor.farm.owner_id,
                    farm_id=motor.farm_id,
                    motor_id=motor.id,
                    category="MOTOR",
                    title_en=f"Pipeline Switched to Line {next_pipeline_idx}",
                    title_ta=f"பாசனம் பைப்லைன் {next_pipeline_idx}-க்கு மாறியது",
                    message_en=f"Completed {active_pipe.target_rotations} rotations on {active_pipe.name}. Now irrigating {next_pipe.name}.",
                    message_ta=f"{active_pipe.name}-ல் {active_pipe.target_rotations} சுற்றுகள் நிறைவடைந்தது. தற்போது {next_pipe.name} பாசனம் பெறுகிறது.",
                    severity="INFO"
                )
                db.add(notif)

        db.commit()
        return {
            "current_pipeline": active_pipe.pipeline_index,
            "actual_rotations": active_pipe.actual_rotations,
            "target_rotations": active_pipe.target_rotations,
            "transition_occurred": transition_occurred,
            "next_pipeline_index": next_pipeline_idx,
            "status": active_pipe.status
        }

    def trigger_obstruction_fault(
        self,
        db: Session,
        motor: Motor,
        pipeline_index: int,
        details: str = "Rotary actuator jammed or position switch timeout"
    ) -> FaultEvent:
        """
        Triggers emergency safety state when rotary distributor is mechanically obstructed.
        """
        pipelines = self.get_motor_pipelines(db, motor.id)
        active_pipe = next((p for p in pipelines if p.pipeline_index == pipeline_index), None)
        if active_pipe:
            active_pipe.status = "OBSTRUCTED"
            active_pipe.fault_reason = details

        # Update motor status to FAULT
        motor.status = "FAULT"
        motor.last_status_change = datetime.now(timezone.utc)

        # Create FaultEvent
        fault = FaultEvent(
            device_id=motor.device_id or "UNKNOWN",
            motor_id=motor.id,
            fault_code="PIPELINE_OBSTRUCTION",
            fault_name=f"Mechanical Jam on Pipeline {pipeline_index}",
            severity="CRITICAL",
            is_active=True,
            farmer_explanation_en=f"Mechanical distributor stopped rotating on pipeline {pipeline_index}. The motor has been stopped safely to protect the gearbox and pipes.",
            farmer_explanation_ta=f"பைப்லைன் {pipeline_index}-ல் சுழலும் வால்வு அடைப்பு ஏற்பட்டுள்ளது. மோட்டார் மற்றும் கியர்பாக்ஸைப் பாதுகாக்க மோட்டார் பாதுகாப்பாக நிறுத்தப்பட்டது.",
            safe_action_en="Inspect the 7-way rotary distributor for physical stones or mud obstruction before restarting. Do NOT force the motor relay manually.",
            safe_action_ta="மோட்டாரை மீண்டும் இயக்குவதற்கு முன் 7-வழி சுழல் வால்வில் கல் அல்லது சேறு அடைத்துள்ளதா என சரிபார்க்கவும். சுவிட்சை வலுக்கட்டாயமாக அழுத்த வேண்டாம்."
        )
        db.add(fault)

        # Notification
        notif = Notification(
            user_id=motor.farm.owner_id,
            farm_id=motor.farm_id,
            motor_id=motor.id,
            category="SAFETY",
            title_en=f"CRITICAL: Pipeline {pipeline_index} Obstructed",
            title_ta=f"எச்சரிக்கை: பைப்லைன் {pipeline_index} சுழல் வால்வு அடைப்பு",
            message_en=fault.farmer_explanation_en,
            message_ta=fault.farmer_explanation_ta,
            severity="CRITICAL"
        )
        db.add(notif)
        db.commit()
        db.refresh(fault)
        return fault

    def reset_pipeline_sequence(self, db: Session, motor_id: str, start_index: int = 1):
        pipelines = self.get_motor_pipelines(db, motor_id)
        for p in pipelines:
            p.actual_rotations = 0
            p.fault_reason = None
            if p.pipeline_index == start_index:
                p.status = "FLOWING"
            else:
                p.status = "IDLE"
        db.commit()

pipeline_service = PipelineStateMachine()
