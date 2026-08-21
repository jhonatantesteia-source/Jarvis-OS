# JARVIS OS

Local-first intelligent desktop assistant for Windows.

## Milestone 0 — Foundation

Foundation for an Electron + React desktop shell and Python Core. This milestone intentionally excludes LLM, voice, autonomous agents and the complex neural HUD.

## Architecture

```text
Electron + React + TypeScript
            │ HTTP / localhost
            ▼
        Python Core
     ┌──────┼────────┐
     API   Events   Database
           Logging
```

## Requirements

- Windows 10/11 x64
- Python 3.13+
- Node.js LTS
- npm
- Git

## Setup

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
npm install
```

Start the Python Core:

```powershell
python -m core
```

Health endpoint: `http://127.0.0.1:8765/health`

In another terminal:

```powershell
npm run dev
```

## Acceptance criteria

- Python Core starts without exceptions.
- `/health` returns `status=online`.
- Electron launches the React renderer.
- Renderer can read backend health.
- SQLite database is initialized.
- Logs are written to `logs/`.
- Secrets are excluded from Git.

## Milestone 1 — Garmin device recognition

Local-first detection of a Garmin watch connected via USB (Mass Storage
mode), no Garmin Connect / Strava / cloud dependency. See
`docs/ARCHITECTURE.md` for the data flow.

```powershell
# com o relógio conectado e montado como unidade (ex.: E:\)
curl -X POST http://127.0.0.1:8765/integrations/garmin/scan
curl http://127.0.0.1:8765/integrations/garmin/status
curl http://127.0.0.1:8765/integrations/garmin/diagnostics
python -m integrations.garmin.diagnostics
```

Acceptance criteria:

- Python Core starts a background poller that detects a connected watch
  without any manual request (checks every 5s).
- `POST /integrations/garmin/scan` forces an immediate check and returns
  the current status.
- `GET /integrations/garmin/status` returns the last known status without
  touching the filesystem.
- Connecting/disconnecting the watch publishes `garmin.device.connected`
  / `garmin.device.disconnected` on the Event Bus and records the event
  in `system_events`.
- All of `integrations/garmin/tests/` and `tests/test_garmin_api.py` pass
  without the physical device (fixtures only).
- The diagnostic CLI can be run with `python -m integrations.garmin.diagnostics`
  when the watch is connected, or with `--path` against a fixture directory.

## Roadmap

Foundation → LLM → Windows Tools → Memory → Skills → Voice → Agents → Neural HUD → Proactivity → Production Packaging.
