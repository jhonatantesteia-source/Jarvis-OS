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

## Milestone 2 — OpenJarvis Foundation

Implementation of the core agent loop and security boundary.

Architecture:
LLM → AgentRuntime → ToolInvocationBoundary → PolicyEngine → ToolExecutor → Tool.

Key features:
- Provider-agnostic LLM interface.
- Deterministic fake LLM for testing.
- Local Ollama integration.
- Fail-closed security policy (DENY by default).
- Risk-based authorization (LOW, MEDIUM, HIGH, CRITICAL).

## Milestone 3 — Persistent Memory

Introduction of a local-first persistent memory subsystem.

Architecture:
AgentRuntime → MemoryProvider → LocalFileMemoryProvider → JSON storage.

Key features:
- MemoryEntry model (ID, content, timestamp, metadata).
- Deterministic storage and retrieval.
- Memory tools integrated into the Agent loop (store, retrieve, list, delete).
- Persistence survives process restarts.

Limitations:
- Exact-ID retrieval only (no semantic search).
- Flat global memory space.

## Milestone 4 — Human-in-the-Loop (HITL)

Transformation of approval requests into a secure authorization workflow.

Architecture:
LLM → AgentRuntime → ToolInvocationBoundary → PolicyEngine → ApprovalProvider → ApprovalGrant → ToolExecutor → Tool.

Key features:
- ApprovalProvider abstraction for asynchronous human decisions.
- ApprovalGrant: Bound tokens ensuring exact tool and argument match.
- Replay Protection: Single-use grants via in-memory tracking.
- Expiration: Time-to-live (TTL) enforced at the final execution gate.
- Fail-Closed: Any provider failure or denied decision blocks execution.

Security Hardening (Post-Implementation):
- Strict Argument Validation: Pydantic-based schema enforcement that rejects unknown arguments.
- Internal Invocation Identity: System-generated UUIDs for security correlation, preventing LLM-controlled IDs.
- Strict Expiration: Grants are invalid exactly at and after the expiration timestamp.
- Exception Sanitization: User-facing errors are cleaned to prevent internal information disclosure.
- Security Audit Events: Structured logging of all authorization decisions and execution outcomes.

Future Security Requirements:
- Memory authorization hardening: Distinguishing between retrieval (read), store (write), and deletion (mutation) risk levels.

## Roadmap

Foundation → LLM → Windows Tools → Memory → HITL → Skills → Voice → Agents → Neural HUD → Proactivity → Production Packaging.
