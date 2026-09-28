# AttackWeave

An explainable cyberattack reconstruction platform built for BYTEATHON 2026.

## Features

- Secure account creation and sign-in using PBKDF2 password hashing
- SQLite-backed stored investigations
- JSON telemetry upload and attack-stage classification
- Correlated attack timeline, MITRE ATT&CK mappings, and risk scoring
- Lateral-movement forecast for a high-value domain controller
- Actionable containment workflow and an explainable incident copilot

## Run locally

```powershell
python server.py
```

Open `http://localhost:8000`, create an analyst account, then select **Simulate attack**.

The project uses only Python's standard library, so no package installation is required.
