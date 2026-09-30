"""Diagnóstico seguro do dispositivo Garmin para testes de bancada.

Este módulo NÃO importa nem altera atividades. Ele apenas verifica se uma
unidade Garmin está montada, valida o GarminDevice.xml e faz um inventário
leve dos arquivos encontrados. Isso permite testar o hardware real antes de
implementar o scanner/importador de FIT.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from integrations.garmin.detector import find_garmin_device


@dataclass(frozen=True)
class GarminDiagnostics:
    connected: bool
    mount_point: str | None
    garmin_root: str | None
    device_id: str | None
    model_description: str | None
    software_version: str | None
    device_xml_valid: bool
    total_files: int
    total_bytes: int
    extensions: dict[str, int]
    top_level_entries: list[str]
    errors: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def run_diagnostics(search_roots: list[Path] | None = None) -> GarminDiagnostics:
    """Executa um diagnóstico somente-leitura.

    ``search_roots`` existe para testes e permite simular unidades sem
    depender de hardware físico.
    """
    device = find_garmin_device(search_roots)
    if device is None:
        return GarminDiagnostics(
            connected=False, mount_point=None, garmin_root=None, device_id=None,
            model_description=None, software_version=None,
            device_xml_valid=False, total_files=0, total_bytes=0,
            extensions={}, top_level_entries=[], errors=["Nenhum dispositivo Garmin detectado."],
        )

    root = device.garmin_root
    errors: list[str] = []
    counts: Counter[str] = Counter()
    total_files = 0
    total_bytes = 0

    try:
        entries = sorted(p.name for p in root.iterdir())
    except OSError as exc:
        entries = []
        errors.append(f"Não foi possível listar {root}: {exc}")

    try:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                total_files += 1
                total_bytes += path.stat().st_size
                suffix = path.suffix.lower() or "<sem_extensão>"
                counts[suffix] += 1
            except OSError as exc:
                errors.append(f"Falha ao ler metadados de {path}: {exc}")
    except OSError as exc:
        errors.append(f"Falha ao percorrer {root}: {exc}")

    return GarminDiagnostics(
        connected=True,
        mount_point=str(device.mount_point),
        garmin_root=str(root),
        device_id=device.device_id,
        model_description=device.model_description,
        software_version=device.software_version,
        device_xml_valid=True,
        total_files=total_files,
        total_bytes=total_bytes,
        extensions=dict(sorted(counts.items())),
        top_level_entries=entries,
        errors=errors,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico local do módulo Garmin do Jarvis OS")
    parser.add_argument("--path", type=Path, help="Raiz simulada/montada a ser testada")
    args = parser.parse_args()

    roots = [args.path] if args.path else None
    result = run_diagnostics(roots)

    print("JARVIS OS — GARMIN DIAGNOSTICS")
    print(f"Connected: {result.connected}")
    if result.device_id:
        print(f"Device ID: {result.device_id}")
        print(f"Model: {result.model_description}")
        print(f"Firmware: {result.software_version}")
        print(f"Mount: {result.mount_point}")
    print(f"Files: {result.total_files}")
    print(f"Bytes: {result.total_bytes}")
    print(f"Extensions: {result.extensions}")
    if result.errors:
        for error in result.errors:
            print(f"ERROR: {error}")
    return 0 if result.connected and result.device_xml_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
