import asyncio
from datetime import datetime, timezone, timedelta
import pytz
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.db.session import SessionLocal
from backend.app.models.entities import Schedule, ScheduleExecution, Motor, Notification
from backend.app.services.device_service import device_manager

class ScheduleEngine:
    def __init__(self):
        self._is_running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._task = asyncio.create_task(self._scheduler_loop())

    def stop(self):
        self._is_running = False
        if self._task:
            self._task.cancel()

    async def _scheduler_loop(self):
        while self._is_running:
            try:
                db = SessionLocal()
                try:
                    await self._evaluate_due_schedules(db)
                finally:
                    db.close()
            except Exception as e:
                print(f"[ScheduleEngine Error] {e}")
            await asyncio.sleep(30)  # Check every 30 seconds

    async def _evaluate_due_schedules(self, db: Session):
        active_schedules = db.query(Schedule).filter(Schedule.is_active == True).all()
        for sched in active_schedules:
            motor = sched.motor
            farm = sched.farm
            if not motor or not farm:
                continue

            # Compute current time in farm's timezone
            tz_str = sched.timezone or farm.timezone or "Asia/Kolkata"
            try:
                farm_tz = pytz.timezone(tz_str)
            except Exception:
                farm_tz = pytz.timezone("Asia/Kolkata")

            now_farm = datetime.now(farm_tz)
            current_time_str = now_farm.strftime("%H:%M")
            current_day_str = now_farm.strftime("%a").lower()  # mon, tue, wed...

            # Check if today is a scheduled day
            scheduled_days = [d.strip().lower() for d in sched.days_of_week.split(",")]
            if current_day_str not in scheduled_days:
                continue

            # Check if start time matches
            if current_time_str == sched.start_time:
                # Check if we already executed this schedule today
                start_of_today = now_farm.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
                existing_exec = db.query(ScheduleExecution).filter(
                    ScheduleExecution.schedule_id == sched.id,
                    ScheduleExecution.planned_start_time >= start_of_today,
                    ScheduleExecution.status.in_(["RUNNING", "COMPLETED", "DISPATCHED"])
                ).first()

                if existing_exec:
                    continue  # Already executed or executing today

                # Prevent starting if motor is in FAULT or already RUNNING
                if motor.status in ["FAULT", "RUNNING"]:
                    continue

                # Create execution record
                planned_utc = datetime.now(timezone.utc)
                execution = ScheduleExecution(
                    schedule_id=sched.id,
                    motor_id=motor.id,
                    planned_start_time=planned_utc,
                    status="DISPATCHED"
                )
                db.add(execution)
                db.commit()

                # Dispatch START command safely
                try:
                    await device_manager.dispatch_command(
                        db=db,
                        motor=motor,
                        command_type="START",
                        parameters={
                            "source": "SCHEDULE",
                            "schedule_id": sched.id,
                            "pipeline_mode": sched.pipeline_mode,
                            "duration_minutes": sched.duration_minutes
                        }
                    )
                    execution.status = "RUNNING"
                    execution.actual_start_time = datetime.now(timezone.utc)

                    notif = Notification(
                        user_id=farm.owner_id,
                        farm_id=farm.id,
                        motor_id=motor.id,
                        category="SCHEDULE",
                        title_en=f"Irrigation Started: {sched.name}",
                        title_ta=f"பாசனம் தொடங்கியது: {sched.name}",
                        message_en=f"Automated schedule {sched.name} started successfully on {motor.name}.",
                        message_ta=f"{motor.name}-ல் திட்டமிடப்பட்ட பாசனம் {sched.name} தொடங்கியது.",
                        severity="INFO"
                    )
                    db.add(notif)
                    db.commit()
                except Exception as ex:
                    execution.status = "FAILED"
                    execution.error_message = str(ex)
                    db.commit()

            # Check if stop time matches or duration exceeded
            elif sched.stop_time and current_time_str == sched.stop_time and motor.status == "RUNNING":
                try:
                    await device_manager.dispatch_command(
                        db=db,
                        motor=motor,
                        command_type="STOP",
                        parameters={"source": "SCHEDULE_STOP", "schedule_id": sched.id}
                    )
                    # Mark active execution as COMPLETED
                    active_exec = db.query(ScheduleExecution).filter(
                        ScheduleExecution.schedule_id == sched.id,
                        ScheduleExecution.status == "RUNNING"
                    ).first()
                    if active_exec:
                        active_exec.status = "COMPLETED"
                        active_exec.actual_end_time = datetime.now(timezone.utc)
                        db.commit()
                except Exception as ex:
                    print(f"[Schedule Stop Error] {ex}")

schedule_engine = ScheduleEngine()
