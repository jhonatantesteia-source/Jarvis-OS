# JARVIS OS Roadmap

1. Foundation — done
2. LLM abstraction and tool calling
3. Windows tools
4. Memory
5. Skills
6. Voice
7. Agents
8. Neural HUD
9. Proactivity
10. Production packaging

First production skill: Ganso → MGV7 → Toledo.

## Garmin module sub-roadmap (integrations/garmin/)

Runs alongside the milestones above, one vertical slice at a time:

1. **Device recognition — done (Milestone 1).** Detects a connected Garmin
   watch via `Garmin/GarminDevice.xml`, publishes `garmin.device.connected`
   / `garmin.device.disconnected`, exposes `GET /integrations/garmin/status`
   and `POST /integrations/garmin/scan`.
2. Scanner + raw file dedup (hash + serial/type/time_created).
3. FIT parser (via the official `garmin-fit-sdk`) for `Activity/`.
4. Normalizer + SQLite schema for activities/laps/records.
5. Monitor/Sleep/Metrics decoding once the parser is validated.
6. Importer orchestration + `garmin.sync.*` / `garmin.activity.*` events.
7. Sports agent + HUD surface.
