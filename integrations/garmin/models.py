"""Modelos de dados do módulo de detecção Garmin.

Os campos de GarminDeviceInfo correspondem exatamente ao que foi
confirmado por análise de um GarminDevice.xml real (Forerunner 245,
firmware 1370) — nenhum campo aqui é especulativo.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class GarminDeviceInfo:
    """Identidade do dispositivo Garmin conectado, extraída do seu GarminDevice.xml."""

    mount_point: Path
    garmin_root: Path
    device_id: str
    model_description: str
    model_part_number: str
    software_version: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["mount_point"] = str(self.mount_point)
        data["garmin_root"] = str(self.garmin_root)
        return data


@dataclass(frozen=True)
class GarminStatus:
    """Snapshot do estado de conexão do módulo — o que a API/HUD consomem."""

    connected: bool
    checked_at: datetime
    device: GarminDeviceInfo | None = None

    def to_dict(self) -> dict:
        return {
            "connected": self.connected,
            "checked_at": self.checked_at.isoformat(),
            "device": self.device.to_dict() if self.device else None,
        }
