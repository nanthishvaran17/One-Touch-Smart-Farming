# Farm Saathi (பார்ம் சாத்தி) — Smart Farmer Irrigation Platform

A production-grade, secure, multilingual smart irrigation platform connecting farmers' mobile applications to real farm motors, 3-phase electrical sensors, persistent automation schedules, and a **seven-pipeline mechanical rotary distributor** (with 5 rotations per line).

---

## Key Features

1. **Voice-First Farmer Assistant**: Spoken Tamil (`தமிழ்`) and English natural language understanding. Supports queries like *"மோட்டார் ஓடுகிறதா?"*, *"போர்வெல் மோட்டார் போடு"*, and *"Is my motor running?"*.
2. **Dual User Interface**:
   - **Easy Mode**: High-contrast, giant touch targets (>64dp), single primary action, audio confirmations, designed specifically for elderly or low-literacy farmers.
   - **Advanced Mode**: 3-Phase electrical curves (VR, VY, VB, IR, IY, IB), power calculations, water flow meters (LPM), and technician diagnostic tools.
3. **Seven-Pipeline Mechanical System**:
   - Configurable state machine driving a 7-way rotary distributor.
   - Enforces 5 full rotations per pipeline before advancing to the next line.
   - Position sensing, rotation pulse counting, and automatic obstruction jamming detection with motor safety cutoff.
4. **Hardware & Electrical Safety**:
   - Independent controller-side threshold enforcement (under/over voltage, overload current, dry-run current).
   - Real command lifecycle (`CREATED` -> `SENT` -> `ACKNOWLEDGED` -> `EXECUTING` -> `SUCCEEDED` / `FAILED`).
   - Idempotency keys prevent duplicate motor starts.
5. **Durable Schedules**:
   - Timezone-aware persistent scheduling engine with execution tracking.
   - Automatic retry and power recovery.
6. **Built-in Hardware Simulator**:
   - Emulates physical controller `FS-CTRL-88219` driving 7.5 HP motors.
   - Generates authentic 3-phase telemetry, advances the 7 pipelines sequentially with 5 rotations each, and allows technician fault injection (voltage sag, overload, dry run, mechanical obstruction) for safe testing without high-voltage physical wiring!

---

## Quick Start (Run Locally)

### 1. Backend Setup (FastAPI & Database)

Ensure Python 3.10+ is installed:

```bash
# Initialize database tables and seed authoritative farm data
python -m backend.app.db.init_db

# Run automated tests
python -m pytest backend/tests/test_all_features.py -v

# Start FastAPI Backend Server with WebSocket support
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API server starts at `http://127.0.0.1:8000`.
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Live WebSocket: `ws://127.0.0.1:8000/api/v1/ws/live`

### 2. Frontend Setup (React & Vite)

```bash
cd frontend
npm install
npm run dev
```

The frontend will run at `http://localhost:5173`.

---

## Demo Account Credentials

- **Phone Number**: `9876543210`
- **Password**: `FarmerPass123!`
- **Preferred Language**: Tamil (`ta`) or English (`en`)
- **Default Farm**: Green Acres Farm (Pollachi, Tamil Nadu)
- **Default Controller**: `FS-CTRL-88219` (Online)
- **Default Motor**: Borewell Motor (7.5 HP Submersible with 7 Pipelines configured for 5 rotations each)

---

## Project Structure

```
Farmar/
├── backend/
│   ├── alembic/                # Database schema migrations
│   ├── app/
│   │   ├── api/                # REST endpoints (auth, motors, commands, pipelines, etc.)
│   │   ├── core/               # App configuration & JWT/bcrypt security
│   │   ├── db/                 # SQLAlchemy sessions, engine, and seed script
│   │   ├── models/             # Relational entities (User, Motor, Pipeline, Telemetry, etc.)
│   │   ├── schemas/            # Pydantic validation schemas
│   │   └── services/           # Device manager, 7-pipeline state machine, scheduler, voice engine
│   └── tests/                  # Pytest test suite & Locust load test
├── frontend/
│   ├── src/
│   │   ├── api.ts              # Typed API client and WebSocket handlers
│   │   ├── i18n.ts             # Bilingual Tamil/English translation dictionary
│   │   ├── App.tsx             # Main accessible UI with Easy/Advanced modes
│   │   └── index.css           # Vanilla CSS design system with custom farm tokens
├── docs/
│   ├── HARDWARE_INTEGRATION_GUIDE.md  # Wiring, limits, and IoT MQTT/HTTP packets
│   └── SCALABILITY_10M_USERS.md       # 10 Million users capacity plan
└── alembic.ini                 # Alembic migration configuration
```
