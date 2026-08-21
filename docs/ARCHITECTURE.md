# JARVIS OS — Architecture

## Milestone 0

Electron/React is the presentation layer. Python Core owns system state and orchestration. Communication is local HTTP for the foundation; WebSocket/event streaming will be added when real-time task execution is introduced.

## Milestone 1 — Garmin device recognition

First integration under `integrations/`. Local-first: the Garmin watch is
recognized as a USB mass-storage device, no Garmin Connect / Strava / cloud
dependency.

```text
Garmin watch (USB)
      │ mounts as removable drive
      ▼
integrations/garmin/detector.py   — finds Garmin/GarminDevice.xml, parses model/serial
      │
      ▼
integrations/garmin/monitor.py    — polls the detector, tracks connected/disconnected
      │                              transitions, is the only piece that talks to Core
      ├──▶ core/events/bus.py        publish garmin.device.connected / .disconnected
      ├──▶ core/database/connection  record_event() → system_events (audit trail)
      └──▶ core/api/routes/garmin.py GET /integrations/garmin/status
                                      POST /integrations/garmin/scan
```

Scope of Milestone 1 is connection recognition only — reading/importing
activities, sleep and daily metrics from the FIT files is a later increment
(see docs/ROADMAP.md and `integrations/garmin/` module docstring). No new
Python dependency was needed: `GarminDevice.xml` parsing uses the stdlib
`xml.etree.ElementTree`.

## Future

User → Voice/HUD → Core → LLM Router / Planner / Memory / Agents / Skills / Tool Executor → Windows / Browser / ERP / APIs / Garmin activity data.
