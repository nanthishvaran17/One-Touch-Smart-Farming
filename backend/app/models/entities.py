import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Enum, JSON, Index
)
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

def get_utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    preferred_language = Column(String(10), default="ta")  # 'ta' (Tamil) or 'en' (English)
    role = Column(String(30), default="farmer")  # farmer, farm_manager, technician, support, admin
    is_active = Column(Boolean, default=True)
    ui_mode = Column(String(20), default="easy")  # 'easy' or 'advanced'
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    farms = relationship("Farm", back_populates="owner", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token = Column(String(500), nullable=False, index=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

class Farm(Base):
    __tablename__ = "farms"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    location = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timezone = Column(String(50), default="Asia/Kolkata")
    acreage = Column(Float, default=5.0)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    owner = relationship("User", back_populates="farms")
    devices = relationship("Device", back_populates="farm", cascade="all, delete-orphan")
    motors = relationship("Motor", back_populates="farm", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="farm", cascade="all, delete-orphan")

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    serial_number = Column(String(64), unique=True, nullable=False, index=True)
    pairing_token_hash = Column(String(255), nullable=False)
    device_name = Column(String(100), default="Farm Master Controller")
    is_paired = Column(Boolean, default=False)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="SET NULL"), nullable=True, index=True)
    ip_address = Column(String(50), nullable=True)
    firmware_version = Column(String(30), default="v2.4.0-prod")
    status = Column(String(20), default="ONLINE")  # ONLINE, OFFLINE, FAULT
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    farm = relationship("Farm", back_populates="devices")
    motors = relationship("Motor", back_populates="device")
    telemetry_logs = relationship("Telemetry", back_populates="device")

class Motor(Base):
    __tablename__ = "motors"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(100), nullable=False)  # e.g. "Borewell Motor", "Field Motor 1"
    motor_type = Column(String(50), default="submersible")
    hp_rating = Column(Float, default=7.5)
    relay_channel = Column(Integer, default=1)
    status = Column(String(20), default="STOPPED")  # STOPPED, STARTING, RUNNING, STOPPING, FAULT, OFFLINE
    last_status_change = Column(DateTime(timezone=True), default=get_utc_now)
    total_runtime_hours = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    farm = relationship("Farm", back_populates="motors")
    device = relationship("Device", back_populates="motors")
    safety_config = relationship("MotorSafetyConfig", back_populates="motor", uselist=False, cascade="all, delete-orphan")
    pipelines = relationship("MotorPipeline", back_populates="motor", cascade="all, delete-orphan", order_by="MotorPipeline.pipeline_index")
    commands = relationship("MotorCommand", back_populates="motor", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="motor", cascade="all, delete-orphan")
    faults = relationship("FaultEvent", back_populates="motor", cascade="all, delete-orphan")

class MotorSafetyConfig(Base):
    __tablename__ = "motor_safety_configs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    motor_id = Column(String(36), ForeignKey("motors.id", ondelete="CASCADE"), unique=True, nullable=False)
    min_voltage = Column(Float, default=180.0)
    max_voltage = Column(Float, default=260.0)
    max_current = Column(Float, default=24.0)
    dry_run_current = Column(Float, default=8.0)
    max_runtime_minutes = Column(Integer, default=360)
    star_delta_delay_seconds = Column(Integer, default=6)
    dry_run_trip_delay_seconds = Column(Integer, default=15)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    motor = relationship("Motor", back_populates="safety_config")

class MotorPipeline(Base):
    __tablename__ = "motor_pipelines"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    motor_id = Column(String(36), ForeignKey("motors.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_index = Column(Integer, nullable=False)  # 1 to 7
    name = Column(String(100), nullable=False)  # e.g., "Pipeline 1 - South Canal"
    target_rotations = Column(Integer, default=5)  # 5 rotations requirement
    actual_rotations = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True)
    status = Column(String(20), default="IDLE")  # IDLE, ROTATING, FLOWING, COMPLETED, FAULT, OBSTRUCTED
    flow_rate_lpm = Column(Float, default=0.0)
    last_verified_position = Column(Integer, default=1)
    fault_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    motor = relationship("Motor", back_populates="pipelines")

    __table_args__ = (
        Index("idx_motor_pipeline_index", "motor_id", "pipeline_index", unique=True),
    )

class MotorCommand(Base):
    __tablename__ = "motor_commands"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    motor_id = Column(String(36), ForeignKey("motors.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    idempotency_key = Column(String(64), unique=True, nullable=False, index=True)
    command_type = Column(String(30), nullable=False)  # START, STOP, ROTATE_PIPELINE, EMERGENCY_STOP
    parameters = Column(JSON, default=dict)
    status = Column(String(25), default="CREATED")  # CREATED, QUEUED, SENT, ACKNOWLEDGED, EXECUTING, SUCCEEDED, REJECTED, TIMED_OUT, FAILED, CANCELLED
    transport_ack_at = Column(DateTime(timezone=True), nullable=True)
    physical_ack_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(String(255), nullable=True)
    feedback_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    motor = relationship("Motor", back_populates="commands")

class Schedule(Base):
    __tablename__ = "schedules"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    motor_id = Column(String(36), ForeignKey("motors.id", ondelete="CASCADE"), nullable=False, index=True)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    schedule_type = Column(String(20), default="DAILY")  # ONE_TIME, DAILY, WEEKDAYS, WEEKLY
    days_of_week = Column(String(50), default="mon,tue,wed,thu,fri,sat,sun")
    start_time = Column(String(10), nullable=False)  # "06:00" in 24hr format
    stop_time = Column(String(10), nullable=True)   # "08:00"
    duration_minutes = Column(Integer, default=120)
    pipeline_mode = Column(String(30), default="ALL_7_SEQUENTIAL")  # SINGLE, ALL_7_SEQUENTIAL, CUSTOM
    pipeline_sequence = Column(JSON, default=lambda: [1, 2, 3, 4, 5, 6, 7])
    is_active = Column(Boolean, default=True)
    timezone = Column(String(50), default="Asia/Kolkata")
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    motor = relationship("Motor", back_populates="schedules")
    farm = relationship("Farm", back_populates="schedules")
    executions = relationship("ScheduleExecution", back_populates="schedule", cascade="all, delete-orphan")

class ScheduleExecution(Base):
    __tablename__ = "schedule_executions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    schedule_id = Column(String(36), ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    motor_id = Column(String(36), ForeignKey("motors.id", ondelete="CASCADE"), nullable=False, index=True)
    planned_start_time = Column(DateTime(timezone=True), nullable=False)
    actual_start_time = Column(DateTime(timezone=True), nullable=True)
    actual_end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(25), default="SCHEDULED")  # SCHEDULED, DISPATCHED, ACKNOWLEDGED, RUNNING, COMPLETED, FAILED, SKIPPED
    error_message = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    schedule = relationship("Schedule", back_populates="executions")

class Telemetry(Base):
    __tablename__ = "telemetry"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    motor_id = Column(String(36), ForeignKey("motors.id", ondelete="CASCADE"), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now, index=True)
    voltage_r = Column(Float, nullable=True)
    voltage_y = Column(Float, nullable=True)
    voltage_b = Column(Float, nullable=True)
    current_r = Column(Float, nullable=True)
    current_y = Column(Float, nullable=True)
    current_b = Column(Float, nullable=True)
    frequency = Column(Float, default=50.0)
    active_power_kw = Column(Float, default=0.0)
    flow_rate_lpm = Column(Float, default=0.0)
    active_pipeline = Column(Integer, default=1)
    current_rotation = Column(Integer, default=0)
    controller_temp_c = Column(Float, default=32.0)
    signal_strength_dbm = Column(Integer, default=-65)
    mains_healthy = Column(Boolean, default=True)
    quality_valid = Column(Boolean, default=True)

    device = relationship("Device", back_populates="telemetry_logs")

class FaultEvent(Base):
    __tablename__ = "fault_events"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    motor_id = Column(String(36), ForeignKey("motors.id", ondelete="CASCADE"), nullable=True, index=True)
    fault_code = Column(String(30), nullable=False)  # OVERLOAD, DRY_RUN, VOLTAGE_FAULT, PHASE_LOSS, PIPELINE_OBSTRUCTION, CONTROLLER_OFFLINE
    fault_name = Column(String(100), nullable=False)
    severity = Column(String(20), default="CRITICAL")  # INFO, WARNING, CRITICAL
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime(timezone=True), default=get_utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    farmer_explanation_en = Column(Text, nullable=False)
    farmer_explanation_ta = Column(Text, nullable=False)
    safe_action_en = Column(Text, nullable=False)
    safe_action_ta = Column(Text, nullable=False)

    motor = relationship("Motor", back_populates="faults")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=True, index=True)
    motor_id = Column(String(36), ForeignKey("motors.id", ondelete="SET NULL"), nullable=True)
    category = Column(String(30), default="MOTOR")  # MOTOR, SCHEDULE, SAFETY, SYSTEM
    title_en = Column(String(150), nullable=False)
    title_ta = Column(String(150), nullable=False)
    message_en = Column(Text, nullable=False)
    message_ta = Column(Text, nullable=False)
    severity = Column(String(20), default="INFO")  # INFO, WARNING, CRITICAL
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    user = relationship("User", back_populates="notifications")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(64), nullable=True)
    payload = Column(JSON, default=dict)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now)

    user = relationship("User", back_populates="audit_logs")
