# Farm Saathi — Hardware & Embedded Controller Integration Guide

This guide documents the physical interfaces, wiring protocols, and JSON packet structures required to connect real farm controllers (e.g., ESP32, STM32, or industrial Raspberry Pi CM4) to the **Farm Saathi** platform.

---

## 1. Mechanical Product: 7-Pipeline Rotary Distributor

The mechanical product consists of an electrically driven rotary multiport distributor valve feeding 7 distinct irrigation pipeline outlets:

- **Position Sensing**:
  - Mechanical Limit Switch or Hall Effect Sensor at Index Position (Pipeline 1 home marker).
  - High-precision optical encoder or reed switch pulse per distributor rotation.
- **Cycle Configuration**:
  - **Requirement**: 5 full rotations per pipeline before advancing the indexer to the next pipeline.
  - Total sequence: Pipeline 1 (5 rotations) -> Line 2 (5 rotations) -> ... -> Line 7 (5 rotations).
- **Obstruction Protection**:
  - Current sensing on the 12V/24V DC stepper/gear motor.
  - If current exceeds 2.8A for > 800ms or pulse timeout exceeds 15 seconds, controller immediately cuts motor power, issues `OBSTRUCTION` error, and latches safety relay.

---

## 2. Electrical Wiring & Interlocks

| Component | Sensor / Actuator Type | Controller Pin / Interface | Safety Limit |
| :--- | :--- | :--- | :--- |
| **Main Motor Contactor** | 415V 3-Phase Contactor with 240V AC Coil | Relay Channel 1 (Normally Open) with mechanical interlock | Max run time limit: 360 min |
| **Voltage Sensor** | ZMPT101B 3-Phase Voltage Transformer | ADC Pins A0, A1, A2 (Calibrated RMS) | Safe: 180V – 265V |
| **Current Sensor** | SCT-013-030 Non-invasive CT Sensor (30A) | ADC Pins A3, A4, A5 | Max: 22.5A (7.5 HP) • Dry-run: < 7.0A |
| **Rotary Pulse Switch** | NPN Inductive Proximity Sensor (LJ12A3-4-Z/BX) | GPIO 18 (Hardware Interrupt FALLING) | 5 pulses per pipeline |
| **Water Flow Meter** | YF-DN50 2-Inch Hall Effect Flow Sensor | GPIO 19 (Pulse Counter) | > 15 LPM when motor is RUNNING |
| **Local E-Stop** | 22mm Mushroom Emergency Stop Pushbutton | Hardwired inline with contactor coil + GPIO 23 | Immediate hardware latch cut |

---

## 3. IoT JSON Packet Specification

### A. Device Heartbeat & Telemetry (Push every 2 to 10 seconds)
**Topic / Endpoint:** `POST /api/v1/devices/telemetry` or MQTT `farms/{farm_id}/devices/{device_id}/telemetry`

```json
{
  "device_serial": "FS-CTRL-88219",
  "motor_id": "optional-uuid",
  "voltage_r": 231.5,
  "voltage_y": 229.0,
  "voltage_b": 232.0,
  "current_r": 14.8,
  "current_y": 14.6,
  "current_b": 14.9,
  "frequency": 50.0,
  "flow_rate_lpm": 44.5,
  "active_pipeline": 2,
  "current_rotation": 3,
  "controller_temp_c": 34.2,
  "signal_strength_dbm": -64,
  "mains_healthy": true
}
```

### B. Command Payload (Cloud to Device)
```json
{
  "type": "MOTOR_COMMAND",
  "command_id": "d930219c-49a8-4e89-a212-...",
  "idempotency_key": "CMD-borewell-1729172000-a8f3b2",
  "relay_channel": 1,
  "action": "START",
  "parameters": {
    "pipeline_mode": "ALL_7_SEQUENTIAL",
    "duration_minutes": 90
  }
}
```

### C. Command Acknowledgement (Device to Cloud)
```json
{
  "type": "COMMAND_ACK",
  "command_id": "d930219c-49a8-4e89-a212-...",
  "ack_type": "PHYSICAL",
  "status": "SUCCEEDED",
  "feedback_data": {
    "contactor": "CLOSED",
    "verified_current": 14.8,
    "flow_detected": true
  }
}
```
