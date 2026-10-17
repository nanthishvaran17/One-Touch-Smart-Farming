import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Set
from sqlalchemy.orm import Session
from backend.app.models.entities import Telemetry, Device, Motor, FaultEvent, Notification
from backend.app.core.config import settings

class TelemetryBroadcaster:
    def __init__(self):
        # Connected web client websocket connections
        self._listeners: Set[Any] = set()

    def add_listener(self, ws: Any):
        self._listeners.add(ws)

    def remove_listener(self, ws: Any):
        self._listeners.discard(ws)

    async def broadcast(self, message: dict):
        dead_connections = []
        for ws in self._listeners:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)
        for dead in dead_connections:
            self._listeners.discard(dead)

telemetry_broadcaster = TelemetryBroadcaster()

def process_incoming_telemetry(db: Session, data: Dict[str, Any]) -> Telemetry:
    """
    Validates, persists, checks electrical safety thresholds, and broadcasts real telemetry.
    """
    device_sn = data.get("device_serial") or data.get("device_id")
    device = db.query(Device).filter(
        (Device.serial_number == device_sn) | (Device.id == device_sn)
    ).first()

    if not device:
        raise ValueError(f"Unauthorized or unregistered device: {device_sn}")

    # Update device heartbeat and status
    now = datetime.now(timezone.utc)
    device.last_heartbeat = now
    device.status = "ONLINE"

    # Identify motor
    motor_id = data.get("motor_id")
    motor = None
    if motor_id:
        motor = db.query(Motor).filter(Motor.id == motor_id).first()
    if not motor and device.motors:
        motor = device.motors[0]

    # Validate physical plausibility
    vr = float(data.get("voltage_r", 230.0))
    vy = float(data.get("voltage_y", 228.0))
    vb = float(data.get("voltage_b", 231.0))
    ir = float(data.get("current_r", 0.0))
    iy = float(data.get("current_y", 0.0))
    ib = float(data.get("current_b", 0.0))
    flow = float(data.get("flow_rate_lpm", 0.0))
    temp = float(data.get("controller_temp_c", 32.0))
    freq = float(data.get("frequency", 50.0))
    active_pipe = int(data.get("active_pipeline", 1))
    rotation = int(data.get("current_rotation", 0))

    # Reject impossible values
    if any(v < 0 or v > 600 for v in [vr, vy, vb]):
        raise ValueError("Voltage reading outside valid physical limits (0-600V)")
    if any(i < 0 or i > 250 for i in [ir, iy, ib]):
        raise ValueError("Current reading outside valid physical limits (0-250A)")

    avg_voltage = (vr + vy + vb) / 3.0
    avg_current = (ir + iy + ib) / 3.0
    active_power = (1.732 * avg_voltage * avg_current * 0.85) / 1000.0 if avg_current > 1.0 else 0.0

    # Create telemetry record
    telemetry = Telemetry(
        device_id=device.id,
        motor_id=motor.id if motor else None,
        timestamp=now,
        voltage_r=vr,
        voltage_y=vy,
        voltage_b=vb,
        current_r=ir,
        current_y=iy,
        current_b=ib,
        frequency=freq,
        active_power_kw=round(active_power, 2),
        flow_rate_lpm=flow,
        active_pipeline=active_pipe,
        current_rotation=rotation,
        controller_temp_c=temp,
        signal_strength_dbm=int(data.get("signal_strength_dbm", -65)),
        mains_healthy=bool(data.get("mains_healthy", True)),
        quality_valid=True
    )
    db.add(telemetry)

    # Check motor safety limits if motor exists
    if motor and motor.safety_config:
        cfg = motor.safety_config
        # 1. Voltage Fault
        if avg_voltage < cfg.min_voltage:
            _record_fault(
                db, device, motor, "UNDER_VOLTAGE",
                f"Low Voltage Warning ({avg_voltage:.1f}V)",
                "CRITICAL",
                f"Line voltage dropped to {avg_voltage:.1f}V, below the safe minimum of {cfg.min_voltage}V. Motor stopped to prevent coil burning.",
                f"மின்னழுத்தம் {avg_voltage:.1f}V ஆகக் குறைந்துள்ளது ({cfg.min_voltage}V-க்குக் கீழ்). மோட்டார் பாதுகாப்பாக நிறுத்தப்பட்டது.",
                "Wait for electricity board voltage stabilization before restarting.",
                "மின்சார வாரிய மின்னழுத்தம் சீராகும் வரை காத்திருந்து மீண்டும் இயக்கவும்."
            )
        elif avg_voltage > cfg.max_voltage:
            _record_fault(
                db, device, motor, "OVER_VOLTAGE",
                f"High Voltage Warning ({avg_voltage:.1f}V)",
                "CRITICAL",
                f"Line voltage rose to {avg_voltage:.1f}V, exceeding safe limit {cfg.max_voltage}V.",
                f"மின்னழுத்தம் {avg_voltage:.1f}V ஆக உயர்ந்துள்ளது. பாதுகாப்பிற்காக மோட்டார் நிறுத்தப்பட்டது.",
                "Wait for voltage to return to normal range.",
                "மின்னழுத்தம் இயல்பு நிலைக்கு திரும்பும் வரை காத்திருக்கவும்."
            )

        # 2. Overload Fault
        if avg_current > cfg.max_current:
            _record_fault(
                db, device, motor, "OVERLOAD",
                f"Motor Overload ({avg_current:.1f}A)",
                "CRITICAL",
                f"Current consumption reached {avg_current:.1f}A, exceeding rating {cfg.max_current}A. Bearing or impeller might be jammed.",
                f"மோட்டார் கூடுதல் மின்சாரம் {avg_current:.1f}A எடுக்கிறது. மோட்டாரில் அடைப்பு இருக்கலாம்.",
                "Check pump impeller for sand or debris. Do not force start.",
                "மோட்டாரில் மணல் அல்லது கழிவு அடைத்துள்ளதா என பரிசோதிக்கவும்."
            )

        # 3. Dry-Run Fault (running with current below dry run threshold or zero flow)
        if motor.status == "RUNNING" and avg_current < cfg.dry_run_current and avg_current > 1.0:
            _record_fault(
                db, device, motor, "DRY_RUN",
                "Dry Run Detected (No Water)",
                "CRITICAL",
                f"Motor running with minimal load ({avg_current:.1f}A). Well water level has dropped.",
                f"மோட்டார் தண்ணீர் இன்றி ஓடுகிறது (Dry Run: {avg_current:.1f}A). கிணற்றில் தண்ணீர் மட்டம் குறைந்துள்ளது.",
                "Allow the borewell water table to recharge before starting.",
                "கிணற்றில் நீர் ஊறும் வரை மோட்டாரை இயக்க வேண்டாம்."
            )

    db.commit()
    db.refresh(telemetry)
    return telemetry

def _record_fault(
    db: Session,
    device: Device,
    motor: Motor,
    code: str,
    name: str,
    severity: str,
    exp_en: str,
    exp_ta: str,
    act_en: str,
    act_ta: str
):
    # Check if this active fault already exists
    existing = db.query(FaultEvent).filter(
        FaultEvent.motor_id == motor.id,
        FaultEvent.fault_code == code,
        FaultEvent.is_active == True
    ).first()
    if existing:
        return

    motor.status = "FAULT"
    motor.last_status_change = datetime.now(timezone.utc)

    fault = FaultEvent(
        device_id=device.id,
        motor_id=motor.id,
        fault_code=code,
        fault_name=name,
        severity=severity,
        is_active=True,
        farmer_explanation_en=exp_en,
        farmer_explanation_ta=exp_ta,
        safe_action_en=act_en,
        safe_action_ta=act_ta
    )
    db.add(fault)

    notif = Notification(
        user_id=motor.farm.owner_id,
        farm_id=motor.farm_id,
        motor_id=motor.id,
        category="SAFETY",
        title_en=f"ALERT: {name}",
        title_ta=f"எச்சரிக்கை: {exp_ta[:40]}",
        message_en=exp_en,
        message_ta=exp_ta,
        severity=severity
    )
    db.add(notif)
