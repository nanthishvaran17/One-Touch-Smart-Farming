from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.app.models.entities import Motor, Farm, Schedule, FaultEvent, MotorPipeline

class VoiceIntentEngine:
    """
    Farm Saathi Voice Intent Engine.
    Processes Tamil and English natural queries into deterministic structured operations.
    """

    def process_utterance(
        self,
        db: Session,
        farmer_id: str,
        text: str,
        language: str = "ta"
    ) -> Dict[str, Any]:
        cleaned = text.strip().lower()
        
        # Fetch farmer's motors
        motors = db.query(Motor).join(Farm).filter(Farm.owner_id == farmer_id).all()
        if not motors:
            if language == "ta":
                return {
                    "intent": "NO_MOTORS",
                    "response_text": "உங்கள் கணக்கில் மோட்டார்கள் எதுவும் பதிவு செய்யப்படவில்லை.",
                    "requires_confirmation": False
                }
            return {
                "intent": "NO_MOTORS",
                "response_text": "No motors registered to your account.",
                "requires_confirmation": False
            }

        # Resolve motor if mentioned, else default to first motor
        selected_motor = motors[0]
        for m in motors:
            m_name_lower = m.name.lower()
            if "borewell" in cleaned or "போர்வெல்" in cleaned:
                if "borewell" in m_name_lower or "போர்வெல்" in m_name_lower:
                    selected_motor = m
                    break
            elif "canal" in cleaned or "வாய்க்கால்" in cleaned or "field" in cleaned or "வயல்" in cleaned:
                if "canal" in m_name_lower or "வாய்க்கால்" in m_name_lower or "field" in m_name_lower:
                    selected_motor = m
                    break

        # 1. Intent: CHECK_STATUS ("Is my motor running?", "மோட்டார் ஓடுகிறதா?", "மோட்டார் நிலை என்ன?")
        if any(w in cleaned for w in ["running", "status", "ஓடுதா", "ஓடுகிறதா", "நிலை", "status"]):
            is_running = selected_motor.status == "RUNNING"
            is_fault = selected_motor.status == "FAULT"
            if language == "ta":
                if is_running:
                    msg = f"{selected_motor.name} தற்போது வெற்றிகரமாக ஓடிக் கொண்டிருக்கிறது."
                elif is_fault:
                    msg = f"{selected_motor.name} பிழை காரணமாக நின்றுள்ளது. பாதுகாப்பு தகவலை சரிபார்க்கவும்."
                else:
                    msg = f"{selected_motor.name} தற்போது நிறுத்தப்பட்டுள்ளது (OFF)."
            else:
                if is_running:
                    msg = f"{selected_motor.name} is currently RUNNING."
                elif is_fault:
                    msg = f"{selected_motor.name} is in FAULT state. Please check alerts."
                else:
                    msg = f"{selected_motor.name} is currently STOPPED."
            return {
                "intent": "CHECK_STATUS",
                "motor_id": selected_motor.id,
                "motor_name": selected_motor.name,
                "status": selected_motor.status,
                "response_text": msg,
                "requires_confirmation": False
            }

        # 2. Intent: START_MOTOR ("Start motor", "மோட்டார் போடு", "ஸ்டார்ட் செய்")
        if any(w in cleaned for w in ["start", "on", "போடு", "ஸ்டார்ட்", "இயக்கு"]):
            if selected_motor.status == "RUNNING":
                msg = f"{selected_motor.name} ஏற்கனவே ஓடிக் கொண்டிருக்கிறது." if language == "ta" else f"{selected_motor.name} is already running."
                return {"intent": "START_MOTOR", "motor_id": selected_motor.id, "response_text": msg, "requires_confirmation": False}

            confirm_msg = (
                f"{selected_motor.name}-ஐ இயக்கவா? தயவுசெய்து உறுதிப்படுத்தவும்."
                if language == "ta"
                else f"Do you want to start {selected_motor.name}? Please confirm."
            )
            return {
                "intent": "START_MOTOR",
                "motor_id": selected_motor.id,
                "motor_name": selected_motor.name,
                "action": "START",
                "response_text": confirm_msg,
                "requires_confirmation": True
            }

        # 3. Intent: STOP_MOTOR ("Stop motor", "மோட்டாரை நிறுத்து", "ஆப் செய்")
        if any(w in cleaned for w in ["stop", "off", "நிறுத்து", "ஆப்", "அணை"]):
            if selected_motor.status == "STOPPED":
                msg = f"{selected_motor.name} ஏற்கனவே நிறுத்தப்பட்டுள்ளது." if language == "ta" else f"{selected_motor.name} is already stopped."
                return {"intent": "STOP_MOTOR", "motor_id": selected_motor.id, "response_text": msg, "requires_confirmation": False}

            confirm_msg = (
                f"{selected_motor.name}-ஐ நிறுத்தவா? தயவுசெய்து உறுதிப்படுத்தவும்."
                if language == "ta"
                else f"Do you want to stop {selected_motor.name}? Please confirm."
            )
            return {
                "intent": "STOP_MOTOR",
                "motor_id": selected_motor.id,
                "motor_name": selected_motor.name,
                "action": "STOP",
                "response_text": confirm_msg,
                "requires_confirmation": True
            }

        # 4. Intent: ACTIVE_PIPELINE ("Which pipeline is active?", "எந்த பைப்லைன் ஓடுகிறது?")
        if any(w in cleaned for w in ["pipeline", "பைப்லைன்", "வால்வு", "வழி"]):
            active_pipe = db.query(MotorPipeline).filter(
                MotorPipeline.motor_id == selected_motor.id,
                MotorPipeline.status.in_(["FLOWING", "ROTATING"])
            ).first()
            if not active_pipe:
                active_pipe = selected_motor.pipelines[0] if selected_motor.pipelines else None

            if active_pipe:
                if language == "ta":
                    msg = f"தற்போது பைப்லைன் {active_pipe.pipeline_index} ({active_pipe.name}) செயலில் உள்ளது. சுழற்சி: {active_pipe.actual_rotations}/5."
                else:
                    msg = f"Pipeline {active_pipe.pipeline_index} ({active_pipe.name}) is currently active. Rotations: {active_pipe.actual_rotations}/5."
            else:
                msg = "பைப்லைன் தகவல்கள் கிடைக்கவில்லை." if language == "ta" else "Pipeline information unavailable."

            return {
                "intent": "ACTIVE_PIPELINE",
                "motor_id": selected_motor.id,
                "response_text": msg,
                "requires_confirmation": False
            }

        # 5. Intent: WHY_STOPPED / FAULT QUERY ("Why did motor stop?", "மோட்டார் ஏன் நின்றது?")
        if any(w in cleaned for w in ["why", "stop", "fault", "ஏன்", "காரணம்", "நின்றது"]):
            last_fault = db.query(FaultEvent).filter(
                FaultEvent.motor_id == selected_motor.id
            ).order_by(FaultEvent.started_at.desc()).first()

            if last_fault:
                exp = last_fault.farmer_explanation_ta if language == "ta" else last_fault.farmer_explanation_en
                act = last_fault.safe_action_ta if language == "ta" else last_fault.safe_action_en
                msg = f"{exp} தீர்வு: {act}"
            else:
                msg = "மோட்டாரில் எந்த பிழையும் இல்லை, வழக்கம் போல் நிறுத்தப்பட்டது." if language == "ta" else "No recent faults detected; motor stopped normally."

            return {
                "intent": "WHY_STOPPED",
                "motor_id": selected_motor.id,
                "response_text": msg,
                "requires_confirmation": False
            }

        # 6. Intent: NEXT_SCHEDULE ("Show next irrigation", "அடுத்த பாசனம் எப்போது?")
        if any(w in cleaned for w in ["schedule", "next", "time", "அடுத்த", "நேரம்", "பாசனம்"]):
            sched = db.query(Schedule).filter(
                Schedule.motor_id == selected_motor.id,
                Schedule.is_active == True
            ).first()
            if sched:
                if language == "ta":
                    msg = f"அடுத்த பாசனம் {sched.name} காலை {sched.start_time}-க்கு தொடங்க திட்டமிடப்பட்டுள்ளது."
                else:
                    msg = f"Next irrigation {sched.name} is scheduled at {sched.start_time} ({sched.timezone})."
            else:
                msg = "செயலில் உள்ள திட்டங்கள் எதுவும் இல்லை." if language == "ta" else "No active schedules configured."

            return {
                "intent": "NEXT_SCHEDULE",
                "motor_id": selected_motor.id,
                "response_text": msg,
                "requires_confirmation": False
            }

        # Default fallback
        fallback = (
            "மன்னிக்கவும், நான் புரிந்து கொள்ளவில்லை. 'மோட்டார் ஓடுகிறதா?' அல்லது 'மோட்டார் போடு' என்று கேட்டுப்பாருங்கள்."
            if language == "ta"
            else "Sorry, I didn't catch that. You can ask 'Is my motor running?' or 'Start borewell motor'."
        )
        return {
            "intent": "UNKNOWN",
            "response_text": fallback,
            "requires_confirmation": False
        }

voice_intent_engine = VoiceIntentEngine()
