import asyncio

from integrations.garmin import monitor as monitor_module
from integrations.garmin.models import GarminDeviceInfo
from pathlib import Path


def make_device() -> GarminDeviceInfo:
    return GarminDeviceInfo(
        mount_point=Path("F:/"),
        garmin_root=Path("F:/Garmin"),
        device_id="3324546267",
        model_description="Forerunner 245",
        model_part_number="010-02120-01",
        software_version="13.70",
    )


def test_monitor_background_detects_device(monkeypatch):
    device = make_device()

    detected_devices = [device, None]

    def fake_find_device():
        if detected_devices:
            return detected_devices.pop(0)

        return None

    events = []

    monkeypatch.setattr(
        monitor_module,
        "find_garmin_device",
        fake_find_device,
    )

    monkeypatch.setattr(
        monitor_module,
        "record_event",
        lambda event_name, payload=None: events.append(
            (event_name, payload)
        ),
    )

    monitor = monitor_module.GarminMonitor()

    async def run_test():
        task = asyncio.create_task(
            monitor.run_forever(interval_seconds=0.01)
        )

        await asyncio.sleep(0.05)

        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(run_test())

    event_names = [event[0] for event in events]

    assert "garmin.device.connected" in event_names
    assert "garmin.device.disconnected" in event_names