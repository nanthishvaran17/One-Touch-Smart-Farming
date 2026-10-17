from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class UserRegister(BaseModel):
    phone_number: str = Field(..., example="9876543210")
    full_name: str = Field(..., example="Murugan (முருகன்)")
    password: str = Field(..., min_length=6)
    preferred_language: str = Field("ta", example="ta")
    farm_name: Optional[str] = "Green Acres Farm"
    farm_location: Optional[str] = "Pollachi, Tamil Nadu"
    privacy_consent: bool = True

class UserLogin(BaseModel):
    phone_number: str = Field(..., example="9876543210")
    password: str = Field(..., example="FarmerPass123!")

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserSettingsUpdate(BaseModel):
    full_name: Optional[str] = None
    preferred_language: Optional[str] = None
    ui_mode: Optional[str] = None

# --- Farm Schemas ---
class FarmCreate(BaseModel):
    name: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = "Asia/Kolkata"
    acreage: Optional[float] = 5.0

class FarmOut(BaseModel):
    id: str
    name: str
    location: Optional[str]
    timezone: str
    acreage: float
    created_at: datetime
    class Config:
        from_attributes = True

# --- Motor & Safety Schemas ---
class MotorCreate(BaseModel):
    name: str
    motor_type: str = "submersible"
    hp_rating: float = 7.5
    device_id: Optional[str] = None
    relay_channel: int = 1
    min_voltage: float = 180.0
    max_voltage: float = 265.0
    max_current: float = 22.5
    dry_run_current: float = 7.0
    max_runtime_minutes: int = 360

class MotorUpdate(BaseModel):
    name: Optional[str] = None
    hp_rating: Optional[float] = None
    relay_channel: Optional[int] = None
    device_id: Optional[str] = None

class SafetyConfigUpdate(BaseModel):
    min_voltage: Optional[float] = None
    max_voltage: Optional[float] = None
    max_current: Optional[float] = None
    dry_run_current: Optional[float] = None
    max_runtime_minutes: Optional[int] = None

# --- Command Schemas ---
class CommandCreate(BaseModel):
    command_type: str = Field(..., example="START")  # START, STOP, ROTATE_PIPELINE, EMERGENCY_STOP
    parameters: Optional[Dict[str, Any]] = {}

# --- Pipeline Schemas ---
class PipelineConfigUpdate(BaseModel):
    name: Optional[str] = None
    target_rotations: Optional[int] = 5
    is_enabled: Optional[bool] = True

# --- Schedule Schemas ---
class ScheduleCreate(BaseModel):
    motor_id: str
    name: str
    schedule_type: str = "DAILY"  # ONE_TIME, DAILY, WEEKDAYS, WEEKLY
    days_of_week: str = "mon,tue,wed,thu,fri,sat,sun"
    start_time: str = "06:00"
    stop_time: Optional[str] = "07:30"
    duration_minutes: int = 90
    pipeline_mode: str = "ALL_7_SEQUENTIAL"
    pipeline_sequence: List[int] = [1, 2, 3, 4, 5, 6, 7]
    is_active: bool = True
    timezone: Optional[str] = "Asia/Kolkata"

class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    days_of_week: Optional[str] = None
    start_time: Optional[str] = None
    stop_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    pipeline_mode: Optional[str] = None
    is_active: Optional[bool] = None

# --- Voice Query ---
class VoiceQueryRequest(BaseModel):
    text: str
    language: Optional[str] = "ta"
