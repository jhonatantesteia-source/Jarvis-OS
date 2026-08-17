"""Monitor de conexão do Garmin: detecta transições connected/disconnected,
publica no Event Bus do Jarvis e registra o evento em system_events.

É o único ponto do módulo que sabe sobre o Core (event_bus, database) —
detector.py permanece puro e testável sem nenhuma dependência do Core.
"""
from __future__ import annotations

import asyncio

from loguru import logger

from core.database.connection import record_event
from core.events.bus import event_bus
from integrations.garmin import events as garmin_events
from integrations.garmin.detector import find_garmin_device
from integrations.garmin.models import GarminDeviceInfo, GarminStatus, now_utc

DEFAULT_POLL_INTERVAL_SECONDS = 5.0


class GarminMonitor:
    """Mantém o último estado conhecido do dispositivo e reage a mudanças."""

    def __init__(self) -> None:
        self._device: GarminDeviceInfo | None = None
        self._checked_at = now_utc()
        self._task: asyncio.Task | None = None

    @property
    def status(self) -> GarminStatus:
        """Último estado conhecido — não faz I/O, seguro para polling frequente do HUD."""
        return GarminStatus(connected=self._device is not None, checked_at=self._checked_at, device=self._device)

    def check_once(self) -> GarminStatus:
        """Executa uma detecção síncrona agora e publica eventos se o estado mudou."""
        detected = find_garmin_device()
        self._checked_at = now_utc()
        previous = self._device

        if detected and previous and detected.device_id != previous.device_id:
            # relógio trocado sem uma desconexão observável entre as duas leituras
            self._publish(garmin_events.DEVICE_DISCONNECTED, previous)
            self._device = detected
            self._publish(garmin_events.DEVICE_CONNECTED, detected)
        elif detected and not previous:
            self._device = detected
            self._publish(garmin_events.DEVICE_CONNECTED, detected)
        elif not detected and previous:
            self._publish(garmin_events.DEVICE_DISCONNECTED, previous)
            self._device = None
        else:
            self._device = detected  # sem transição: continua conectado ou continua ausente

        return self.status

    def _publish(self, event_name: str, device: GarminDeviceInfo) -> None:
        payload = device.to_dict()
        logger.info("{} — {} ({})", event_name, device.model_description, device.device_id)
        event_bus.publish(event_name, payload)
        record_event(event_name, payload)

    async def run_forever(self, interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS) -> None:
        """Loop de polling em background; roda até a task ser cancelada."""
        while True:
            await asyncio.to_thread(self.check_once)
            await asyncio.sleep(interval_seconds)

    def start(self, interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS) -> None:
        """Inicia o polling em background (chamado no lifespan da API)."""
        if self._task is None:
            self._task = asyncio.create_task(self.run_forever(interval_seconds))

    async def stop(self) -> None:
        """Cancela o polling em background (chamado no shutdown da API)."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def reset(self) -> None:
        """Limpa o estado conhecido. Uso: isolar testes entre execuções."""
        self._device = None


garmin_monitor = GarminMonitor()
