from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.app.core.config import settings
from backend.app.db.init_db import init_db
from backend.app.api import (
    auth, farms, motors, commands, pipelines, schedules, telemetry, notifications, voice, devices
)
from backend.app.services.schedule_engine import schedule_engine
from backend.app.services.hardware_simulator import hardware_simulator
from backend.app.services.telemetry_service import telemetry_broadcaster

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and authoritative seed data
    init_db()
    # Start schedule engine loop
    schedule_engine.start()
    # Start simulated hardware controller so live 7-pipeline rotation and telemetry flow
    hardware_simulator.start()
    yield
    # Graceful shutdown
    schedule_engine.stop()
    hardware_simulator.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Smart Irrigation, Motor Automation & Farmer Assistance Platform",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers under API v1
api_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=api_prefix)
app.include_router(farms.router, prefix=api_prefix)
app.include_router(motors.router, prefix=api_prefix)
app.include_router(commands.router, prefix=api_prefix)
app.include_router(pipelines.router, prefix=api_prefix)
app.include_router(schedules.router, prefix=api_prefix)
app.include_router(telemetry.router, prefix=api_prefix)
app.include_router(notifications.router, prefix=api_prefix)
app.include_router(voice.router, prefix=api_prefix)
app.include_router(devices.router, prefix=api_prefix)

# WebSocket endpoint for real-time live dashboard
@app.websocket("/api/v1/ws/live")
async def websocket_live_telemetry(websocket: WebSocket):
    await websocket.accept()
    telemetry_broadcaster.add_listener(websocket)
    try:
        while True:
            # Keep socket open and receive any ping / client commands
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        telemetry_broadcaster.remove_listener(websocket)
    except Exception:
        telemetry_broadcaster.remove_listener(websocket)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Farm Saathi Smart Irrigation API",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
