"""Testes HTTP do módulo Garmin — não dependem de dispositivo físico
nem do poller em background (o /scan chama o detector sob demanda)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.api.app import app
from integrations.garmin import monitor as garmin_monitor_module
from integrations.garmin.models import GarminDeviceInfo

DEVICE = GarminDeviceInfo(
    mount_point=Path("E:/"),
    garmin_root=Path("E:/Garmin"),
    device_id="3324546267",
    model_description="Forerunner 245",
    model_part_number="006-B3076-00",
    software_version="1370",
)


@pytest.fixture(autouse=True)
def _isolate_monitor_state():
    """Evita que o estado do monitor global vaze entre testes."""
    garmin_monitor_module.garmin_monitor.reset()
    yield
    garmin_monitor_module.garmin_monitor.reset()


def test_status_reports_disconnected_by_default():
    r = TestClient(app).get("/integrations/garmin/status")
    assert r.status_code == 200
    assert r.json()["connected"] is False
    assert r.json()["device"] is None


def test_scan_reports_connected_device(monkeypatch):
    monkeypatch.setattr("integrations.garmin.monitor.find_garmin_device", lambda: DEVICE)
    monkeypatch.setattr("integrations.garmin.monitor.record_event", lambda *a, **k: None)

    r = TestClient(app).post("/integrations/garmin/scan")
    assert r.status_code == 200
    body = r.json()
    assert body["connected"] is True
    assert body["device"]["device_id"] == "3324546267"
    assert body["device"]["model_description"] == "Forerunner 245"


def test_status_after_scan_reflects_connected_state(monkeypatch):
    monkeypatch.setattr("integrations.garmin.monitor.find_garmin_device", lambda: DEVICE)
    monkeypatch.setattr("integrations.garmin.monitor.record_event", lambda *a, **k: None)

    client = TestClient(app)
    client.post("/integrations/garmin/scan")
    r = client.get("/integrations/garmin/status")
    assert r.json()["connected"] is True


def test_diagnostics_endpoint_uses_diagnostic_service(monkeypatch):
    from integrations.garmin.diagnostics import GarminDiagnostics

    fake = GarminDiagnostics(
        connected=True, mount_point="E:/", garmin_root="E:/Garmin",
        device_id="3324546267", model_description="Forerunner 245",
        software_version="1370", device_xml_valid=True, total_files=2,
        total_bytes=100, extensions={".fit": 1, ".xml": 1},
        top_level_entries=["Activity"], errors=[],
    )
    monkeypatch.setattr("core.api.routes.garmin.run_diagnostics", lambda: fake)

    r = TestClient(app).get("/integrations/garmin/diagnostics")
    assert r.status_code == 200
    body = r.json()
    assert body["connected"] is True
    assert body["device_id"] == "3324546267"
    assert body["extensions"][".fit"] == 1
