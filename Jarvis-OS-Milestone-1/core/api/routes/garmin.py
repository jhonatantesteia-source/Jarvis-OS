"""Endpoints HTTP do módulo de integração Garmin (Milestone 1: só reconhecimento de conexão)."""
from fastapi import APIRouter

from integrations.garmin.monitor import garmin_monitor

router = APIRouter(prefix="/integrations/garmin", tags=["garmin"])


@router.get("/status")
def get_status():
    """Último estado conhecido, sem forçar nova varredura — uso pelo HUD (polling frequente)."""
    return garmin_monitor.status.to_dict()


@router.post("/scan")
def scan_now():
    """Força uma varredura imediata das unidades e atualiza/publica o estado."""
    return garmin_monitor.check_once().to_dict()
