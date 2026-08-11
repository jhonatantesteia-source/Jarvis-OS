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

## Roadmap

Foundation → LLM → Windows Tools → Memory → Skills → Voice → Agents → Neural HUD → Proactivity → Production Packaging.
