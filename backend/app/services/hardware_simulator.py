import asyncio
import random
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.db.session import SessionLocal
from backend.app.models.entities import Device, Motor, MotorCommand, MotorPipeline
from backend.app.services.device_service import device_manager
from backend.app.services.pipeline_service import pipeline_service
from backend.app.services.telemetry_service import process_incoming_telemetry, telemetry_broadcaster

class HardwareControllerSimulator:
    """
    Simulates physical controller 'FS-CTRL-88219' driving a 7.5 HP motor and 7-pipeline rotary distributor.
    Produces authentic 3-phase electrical readings, rotation pulse feedback, and command execution.
    """
    def __init__(self):
        self.device_serial = "FS-CTRL-88219"
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        
        # State variables
        self.contactor_closed = False
        self.active_pipeline = 1
        self.current_rotations = 0
        self.voltage_base = 230.0
        self.current_base = 0.0
        
        # Fault injection flags (for testing safety trips)
        self.simulated_fault: Optional[str] = None  # None, 'UNDER_VOLTAGE', 'OVERLOAD', 'DRY_RUN', 'OBSTRUCTION'

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._task = asyncio.create_task(self._simulation_loop())
            print("[HardwareSimulator] Controller FS-CTRL-88219 started.")

    def stop(self):
        self._is_running = False
        if self._task:
            self._task.cancel()
            print("[HardwareSimulator] Controller FS-CTRL-88219 stopped.")

    def inject_fault(self, fault_type: Optional[str]):
        """Injects a simulated electrical or mechanical fault for testing."""
        self.simulated_fault = fault_type

    async def _simulation_loop(self):
        while self._is_running:
            try:
                db = SessionLocal()
                try:
                    await self._process_pending_commands(db)
                    await self._step_pipeline_and_telemetry(db)
                finally:
                    db.close()
            except Exception as e:
                print(f"[HardwareSimulator Error] {e}")
            await asyncio.sleep(2)  # Emit every 2 seconds

    async def _process_pending_commands(self, db: Session):
        device = db.query(Device).filter(Device.serial_number == self.device_serial).first()
        if not device:
            return

        pending_cmds = db.query(MotorCommand).filter(
            MotorCommand.device_id == device.id,
            MotorCommand.status.in_(["QUEUED", "SENT"])
        ).all()

        for cmd in pending_cmds:
            # Send Transport ACK first
            device_manager.handle_command_ack(
                db=db,
                command_id=cmd.id,
                ack_type="TRANSPORT",
                status="ACKNOWLEDGED"
            )

            # Simulate short contactor delay
            await asyncio.sleep(0.5)

            if cmd.command_type == "START":
                if self.simulated_fault == "OBSTRUCTION":
                    device_manager.handle_command_ack(
                        db=db,
                        command_id=cmd.id,
                        ack_type="PHYSICAL",
                        status="REJECTED",
                        failure_reason="Rotary distributor valve obstructed"
                    )
                    pipeline_service.trigger_obstruction_fault(db, cmd.motor, self.active_pipeline)
                else:
                    self.contactor_closed = True
                    self.current_base = 14.5  # Running current for 7.5 HP motor
                    device_manager.handle_command_ack(
                        db=db,
                        command_id=cmd.id,
                        ack_type="PHYSICAL",
                        status="SUCCEEDED",
                        feedback_data={"contactor": "CLOSED", "flow_rate": 42.5}
                    )
            elif cmd.command_type in ["STOP", "EMERGENCY_STOP"]:
                self.contactor_closed = False
                self.current_base = 0.0
                device_manager.handle_command_ack(
                    db=db,
                    command_id=cmd.id,
                    ack_type="PHYSICAL",
                    status="SUCCEEDED",
                    feedback_data={"contactor": "OPEN", "flow_rate": 0.0}
                )
            elif cmd.command_type == "ROTATE_PIPELINE":
                target_pipe = cmd.parameters.get("pipeline_index", self.active_pipeline + 1)
                if target_pipe > 7:
                    target_pipe = 1
                self.active_pipeline = target_pipe
                self.current_rotations = 0
                device_manager.handle_command_ack(
                    db=db,
                    command_id=cmd.id,
                    ack_type="PHYSICAL",
                    status="SUCCEEDED",
                    feedback_data={"active_pipeline": target_pipe}
                )

    async def _step_pipeline_and_telemetry(self, db: Session):
        device = db.query(Device).filter(Device.serial_number == self.device_serial).first()
        if not device:
            return

        motor = db.query(Motor).filter(Motor.device_id == device.id).first()
        if not motor:
            return

        # Advance mechanical rotations if motor is running
        flow_rate = 0.0
        if self.contactor_closed and motor.status == "RUNNING":
            flow_rate = 42.0 + random.uniform(-1.5, 2.0)
            # Advance rotation pulse
            res = pipeline_service.process_rotation_feedback(
                db=db,
                motor=motor,
                reported_pipeline_idx=self.active_pipeline,
                rotation_pulse_increment=1,
                flow_rate_lpm=flow_rate
            )
            self.current_rotations = res.get("actual_rotations", self.current_rotations)
            if res.get("transition_occurred") and res.get("next_pipeline_index"):
                self.active_pipeline = res.get("next_pipeline_index")
                self.current_rotations = 0

            # Accumulate runtime
            motor.total_runtime_hours += round(2.0 / 3600.0, 4)
            db.commit()

        # Calculate simulated voltage and current based on injected faults
        vr = self.voltage_base + random.uniform(-2.0, 2.0)
        vy = self.voltage_base - 1.5 + random.uniform(-2.0, 2.0)
        vb = self.voltage_base + 1.0 + random.uniform(-2.0, 2.0)

        ir = (self.current_base + random.uniform(-0.3, 0.4)) if self.contactor_closed else 0.0
        iy = (self.current_base - 0.2 + random.uniform(-0.3, 0.4)) if self.contactor_closed else 0.0
        ib = (self.current_base + 0.1 + random.uniform(-0.3, 0.4)) if self.contactor_closed else 0.0

        if self.simulated_fault == "UNDER_VOLTAGE":
            vr, vy, vb = 165.0, 163.0, 167.0
        elif self.simulated_fault == "OVERLOAD":
            ir, iy, ib = 28.5, 29.0, 28.2
        elif self.simulated_fault == "DRY_RUN":
            ir, iy, ib = 4.2, 4.1, 4.3  # below 7A dry-run threshold
            flow_rate = 0.0

        telemetry_payload = {
            "device_serial": self.device_serial,
            "motor_id": motor.id,
            "voltage_r": round(vr, 1),
            "voltage_y": round(vy, 1),
            "voltage_b": round(vb, 1),
            "current_r": round(ir, 1),
            "current_y": round(iy, 1),
            "current_b": round(ib, 1),
            "frequency": 50.0 + random.uniform(-0.1, 0.1),
            "flow_rate_lpm": round(flow_rate, 1),
            "active_pipeline": self.active_pipeline,
            "current_rotation": self.current_rotations,
            "controller_temp_c": round(33.5 + random.uniform(0.0, 0.8), 1),
            "signal_strength_dbm": -62,
            "mains_healthy": True
        }

        # Persist and run electrical safety analysis
        telem = process_incoming_telemetry(db, telemetry_payload)

        # Broadcast live packet to WebSocket dashboard
        broadcast_msg = {
            "type": "TELEMETRY_UPDATE",
            "device_id": device.id,
            "motor_id": motor.id,
            "motor_name": motor.name,
            "motor_status": motor.status,
            "total_runtime_hours": round(motor.total_runtime_hours, 2),
            "telemetry": {
                "timestamp": telem.timestamp.isoformat(),
                "voltage_r": telem.voltage_r,
                "voltage_y": telem.voltage_y,
                "voltage_b": telem.voltage_b,
                "avg_voltage": round((telem.voltage_r + telem.voltage_y + telem.voltage_b) / 3, 1),
                "current_r": telem.current_r,
                "current_y": telem.current_y,
                "current_b": telem.current_b,
                "avg_current": round((telem.current_r + telem.current_y + telem.current_b) / 3, 1),
                "frequency": telem.frequency,
                "active_power_kw": telem.active_power_kw,
                "flow_rate_lpm": telem.flow_rate_lpm,
                "active_pipeline": telem.active_pipeline,
                "current_rotation": telem.current_rotation,
                "controller_temp_c": telem.controller_temp_c,
                "signal_strength_dbm": telem.signal_strength_dbm,
                "mains_healthy": telem.mains_healthy
            }
        }
        await telemetry_broadcaster.broadcast(broadcast_msg)

hardware_simulator = HardwareControllerSimulator()
