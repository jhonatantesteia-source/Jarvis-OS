import json
import sqlite3
from pathlib import Path

from integrations.garmin import monitor as monitor_module
from integrations.garmin.models import GarminDeviceInfo


def make_device() -> GarminDeviceInfo:
    return GarminDeviceInfo(
        mount_point=Path("F:/"),
        garmin_root=Path("F:/Garmin"),
        device_id="3324546267",
        model_description="Forerunner 245",
        model_part_number="010-02120-01",
        software_version="13.70",
    )


def test_garmin_connection_is_recorded_in_sqlite(monkeypatch, tmp_path):
    database_path = tmp_path / "jarvis-test.db"

    def record_test_event(event_name, payload=None):
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_name TEXT NOT NULL,
                    payload TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            connection.execute(
                """
                INSERT INTO system_events (event_name, payload)
                VALUES (?, ?)
                """,
                (
                    event_name,
                    json.dumps(payload) if payload is not None else None,
                ),
            )

            connection.commit()

    monkeypatch.setattr(
        monitor_module,
        "record_event",
        record_test_event,
    )

    monkeypatch.setattr(
        monitor_module,
        "find_garmin_device",
        make_device,
    )

    monitor = monitor_module.GarminMonitor()

    monitor.check_once()

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT event_name, payload
            FROM system_events
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert row is not None
    assert row[0] == "garmin.device.connected"

    payload = json.loads(row[1])

    assert payload["device_id"] == "3324546267"
    assert payload["model_description"] == "Forerunner 245"