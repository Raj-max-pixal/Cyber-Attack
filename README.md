# CyberTrace AI

Multi-Stage Attack Reconstruction & Lateral Movement Prediction Platform.

> From fragmented alerts to one complete attack story.

CyberTrace AI progressively upgrades the existing AttackWeave MVP into a SOC analytics platform for BYTEATHON 2026. Phase 1 establishes normalized telemetry, a modular database foundation, deterministic demo data, and FastAPI APIs while preserving the existing browser console.

## Features

- Secure account creation and sign-in using PBKDF2 password hashing
- SQLite-backed stored investigations
- JSON telemetry upload and attack-stage classification
- Correlated attack timeline, MITRE ATT&CK mappings, and risk scoring
- Lateral-movement forecast for a high-value domain controller
- Actionable containment workflow and an explainable incident copilot

## Phase 1 API

Run `python -m uvicorn backend.app.main:app --reload --port 8001` and open `http://localhost:8001/docs`. Use `POST /api/telemetry/demo`, then `POST /api/analysis/run` with the returned batch ID. JSON and CSV telemetry enter the same normalization service. The database is SQLite by default and can be moved to PostgreSQL with `DATABASE_URL`.

## Run locally

```powershell
python server.py
```

Open `http://localhost:8000`, create an analyst account, then select **Simulate attack**.

The project uses only Python's standard library, so no package installation is required.
