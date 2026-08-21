"""Testes do GarminMonitor — detector e event bus são substituídos por fakes,
então nenhuma varredura real de disco nem escrita no SQLite acontece aqui."""
from datetime import datetime
from pathlib import Path

from core.events.bus import EventBus
from integrations.garmin import events as garmin_events
from integrations.garmin.models import GarminDeviceInfo
from integrations.garmin.monitor import GarminMonitor

DEVICE = GarminDeviceInfo(
    mount_point=Path("E:/"),
    garmin_root=Path("E:/Garmin"),
    device_id="3324546267",
    model_description="Forerunner 245",
    model_part_number="006-B3076-00",
    software_version="1370",
)

OTHER_DEVICE = GarminDeviceInfo(
    mount_point=Path("F:/"),
    garmin_root=Path("F:/Garmin"),
    device_id="9999999999",
    model_description="Fenix 8",
    model_part_number="006-XXXX-00",
    software_version="500",
)


def _build_monitor(monkeypatch, detections):
    """Isola um GarminMonitor: detector fake, event bus fake, sem I/O em disco."""
    it = iter(detections)
    monkeypatch.setattr("integrations.garmin.monitor.find_garmin_device", lambda: next(it))
    fake_bus = EventBus()
    monkeypatch.setattr("integrations.garmin.monitor.event_bus", fake_bus)
    monkeypatch.setattr("integrations.garmin.monitor.record_event", lambda *a, **k: None)

    received: list[tuple[str, dict]] = []
    fake_bus.subscribe(garmin_events.DEVICE_CONNECTED, lambda p: received.append((garmin_events.DEVICE_CONNECTED, p)))
    fake_bus.subscribe(garmin_events.DEVICE_DISCONNECTED, lambda p: received.append((garmin_events.DEVICE_DISCONNECTED, p)))
    return GarminMonitor(), received


def test_publishes_connected_on_first_detection(monkeypatch):
    monitor, received = _build_monitor(monkeypatch, [DEVICE])
    status = monitor.check_once()
    assert status.connected is True
    assert status.device.device_id == DEVICE.device_id
    assert [name for name, _ in received] == [garmin_events.DEVICE_CONNECTED]


def test_no_event_while_still_connected_to_same_device(monkeypatch):
    monitor, received = _build_monitor(monkeypatch, [DEVICE, DEVICE])
    monitor.check_once()
    monitor.check_once()
    assert [name for name, _ in received] == [garmin_events.DEVICE_CONNECTED]


def test_no_event_while_still_disconnected(monkeypatch):
    monitor, received = _build_monitor(monkeypatch, [None, None])
    monitor.check_once()
    monitor.check_once()
    assert received == []


def test_publishes_disconnected_after_removal(monkeypatch):
    monitor, received = _build_monitor(monkeypatch, [DEVICE, None])
    monitor.check_once()
    monitor.check_once()
    assert [name for name, _ in received] == [garmin_events.DEVICE_CONNECTED, garmin_events.DEVICE_DISCONNECTED]


def test_swapping_device_emits_disconnect_then_connect(monkeypatch):
    monitor, received = _build_monitor(monkeypatch, [DEVICE, OTHER_DEVICE])
    monitor.check_once()
    monitor.check_once()
    assert [name for name, _ in received] == [garmin_events.DEVICE_CONNECTED, garmin_events.DEVICE_DISCONNECTED, garmin_events.DEVICE_CONNECTED]
    assert received[-1][1]["device_id"] == OTHER_DEVICE.device_id


def test_status_reflects_last_check(monkeypatch):
    monitor, _ = _build_monitor(monkeypatch, [None])
    status = monitor.check_once()
    assert status.connected is False
    assert status.device is None
    assert isinstance(status.checked_at, datetime)
