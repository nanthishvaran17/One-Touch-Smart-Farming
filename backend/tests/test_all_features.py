import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_login_valid_farmer():
    response = client.post("/api/v1/auth/login", json={
        "phone_number": "9876543210",
        "password": "FarmerPass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["phone_number"] == "9876543210"
    assert data["user"]["preferred_language"] == "ta"

def test_login_invalid_password():
    response = client.post("/api/v1/auth/login", json={
        "phone_number": "9876543210",
        "password": "WrongPassword!"
    })
    assert response.status_code == 401

def test_get_motors_and_pipelines():
    login_res = client.post("/api/v1/auth/login", json={
        "phone_number": "9876543210",
        "password": "FarmerPass123!"
    })
    token = login_res.json()["access_token"]
    farm_id = login_res.json()["user"]["farm_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch motors
    res = client.get(f"/api/v1/farms/{farm_id}/motors", headers=headers)
    assert res.status_code == 200
    motors = res.json()
    assert len(motors) >= 1
    motor = motors[0]
    motor_id = motor["id"]

    # Verify 7-Pipeline configuration
    pipe_res = client.get(f"/api/v1/motors/{motor_id}/pipelines", headers=headers)
    assert pipe_res.status_code == 200
    pipelines = pipe_res.json()
    assert len(pipelines) == 7
    # Verify target rotations is 5
    for p in pipelines:
        assert p["target_rotations"] == 5

def test_motor_command_lifecycle():
    login_res = client.post("/api/v1/auth/login", json={
        "phone_number": "9876543210",
        "password": "FarmerPass123!"
    })
    token = login_res.json()["access_token"]
    farm_id = login_res.json()["user"]["farm_id"]
    headers = {"Authorization": f"Bearer {token}"}

    motors = client.get(f"/api/v1/farms/{farm_id}/motors", headers=headers).json()
    motor_id = motors[0]["id"]

    # Ensure device is online by sending a telemetry heartbeat
    hb_res = client.post("/api/v1/devices/telemetry", json={
        "device_serial": "FS-CTRL-88219",
        "voltage_r": 230.0,
        "current_r": 0.0,
        "flow_rate_lpm": 0.0
    })
    assert hb_res.status_code == 200

    # Dispatch START command
    cmd_res = client.post(f"/api/v1/motors/{motor_id}/commands", json={
        "command_type": "START",
        "parameters": {"test": True}
    }, headers=headers)
    assert cmd_res.status_code == 200
    cmd_data = cmd_res.json()
    assert cmd_data["status"] == "success"
    assert "command_id" in cmd_data
    assert "idempotency_key" in cmd_data

    # Dispatch STOP command
    stop_res = client.post(f"/api/v1/motors/{motor_id}/commands", json={
        "command_type": "STOP",
        "parameters": {"test": True}
    }, headers=headers)
    assert stop_res.status_code == 200

def test_voice_assistant_tamil_and_english():
    login_res = client.post("/api/v1/auth/login", json={
        "phone_number": "9876543210",
        "password": "FarmerPass123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Tamil query: "மோட்டார் நிலை என்ன?"
    va_ta = client.post("/api/v1/voice/query", json={
        "text": "மோட்டார் நிலை என்ன?",
        "language": "ta"
    }, headers=headers)
    assert va_ta.status_code == 200
    res_ta = va_ta.json()
    assert res_ta["intent"] == "CHECK_STATUS"
    assert len(res_ta["response_text"]) > 0

    # English query: "Is my motor running?"
    va_en = client.post("/api/v1/voice/query", json={
        "text": "Is my motor running?",
        "language": "en"
    }, headers=headers)
    assert va_en.status_code == 200
    res_en = va_en.json()
    assert res_en["intent"] == "CHECK_STATUS"
    assert "RUNNING" in res_en["response_text"] or "STOPPED" in res_en["response_text"]

    # Consequential command requires confirmation: "மோட்டார் போடு"
    va_start = client.post("/api/v1/voice/query", json={
        "text": "மோட்டார் போடு",
        "language": "ta"
    }, headers=headers)
    assert va_start.status_code == 200
    assert va_start.json()["requires_confirmation"] is True
