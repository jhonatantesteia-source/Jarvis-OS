import json
import sqlite3
from pathlib import Path

from integrations.garmin import monitor as monitor_module
from integrations.garmin.models import GarminDeviceInfo


def make_device(device_id: str, model: str) -> GarminDeviceInfo:
    return GarminDeviceInfo(
        mount_point=Path("F:/"),
        garmin_root=Path("F:/Garmin"),
        device_id=device_id,
        model_description=model,
        model_part_number="010-02120-01",
        software_version="13.70",
    )


def create_event_recorder(database_path):
    def record_event(event_name, payload=None):
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

    return record_event


def test_garmin_disconnect_is_recorded_in_sqlite(monkeypatch, tmp_path):
    database_path = tmp_path / "jarvis-test.db"

    device = make_device("3324546267", "Forerunner 245")

    monkeypatch.setattr(
        monitor_module,
        "record_event",
        create_event_recorder(database_path),
    )

    detection = {"device": device}

    monkeypatch.setattr(
        monitor_module,
        "find_garmin_device",
        lambda: detection["device"],
    )

    monitor = monitor_module.GarminMonitor()

    # Primeiro ciclo: Garmin conectado.
    monitor.check_once()

    # Segundo ciclo: Garmin desconectado.
    detection["device"] = None
    monitor.check_once()

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT event_name, payload
            FROM system_events
            ORDER BY id
            """
        ).fetchall()

    assert len(rows) == 2

    assert rows[0][0] == "garmin.device.connected"
    assert rows[1][0] == "garmin.device.disconnected"

    connected_payload = json.loads(rows[0][1])
    disconnected_payload = json.loads(rows[1][1])

    assert connected_payload["device_id"] == "3324546267"
    assert disconnected_payload["device_id"] == "3324546267"


def test_garmin_device_swap_is_recorded_in_sqlite(monkeypatch, tmp_path):
    database_path = tmp_path / "jarvis-test.db"

    device_a = make_device(
        "3324546267",
        "Forerunner 245",
    )

    device_b = make_device(
        "9876543210",
        "Forerunner 965",
    )

    monkeypatch.setattr(
        monitor_module,
        "record_event",
        create_event_recorder(database_path),
    )

    detection = {"device": device_a}

    monkeypatch.setattr(
        monitor_module,
        "find_garmin_device",
        lambda: detection["device"],
    )

    monitor = monitor_module.GarminMonitor()

    # Primeiro relógio.
    monitor.check_once()

    # Troca direta para o segundo relógio.
    detection["device"] = device_b
    monitor.check_once()

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT event_name, payload
            FROM system_events
            ORDER BY id
            """
        ).fetchall()

    assert len(rows) == 3

    assert rows[0][0] == "garmin.device.connected"
    assert rows[1][0] == "garmin.device.disconnected"
    assert rows[2][0] == "garmin.device.connected"

    first_disconnect_payload = json.loads(rows[1][1])
    second_connect_payload = json.loads(rows[2][1])

    assert first_disconnect_payload["device_id"] == "3324546267"
    assert second_connect_payload["device_id"] == "9876543210"