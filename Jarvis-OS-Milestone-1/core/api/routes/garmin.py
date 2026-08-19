"""Endpoints HTTP do módulo de integração Garmin."""
from fastapi import APIRouter

from integrations.garmin.diagnostics import run_diagnostics
from integrations.garmin.monitor import garmin_monitor

router = APIRouter(prefix="/integrations/garmin", tags=["garmin"])


@router.get("/status")
def get_status():
    """Último estado conhecido, sem forçar nova varredura."""
    return garmin_monitor.status.to_dict()


@router.post("/scan")
def scan_now():
    """Força uma varredura imediata e atualiza/publica o estado."""
    return garmin_monitor.check_once().to_dict()


@router.get("/diagnostics")
def diagnostics():
    """Executa diagnóstico somente-leitura da unidade Garmin detectada."""
    return run_diagnostics().to_dict()
