import json
import sqlite3
from pathlib import Path
from core.config.settings import ROOT_DIR, settings
def get_connection():
    p = Path(settings.database_path); p = p if p.is_absolute() else ROOT_DIR / p
    p.parent.mkdir(parents=True, exist_ok=True); c = sqlite3.connect(p); c.row_factory = sqlite3.Row; return c
def initialize_database():
    with get_connection() as c:
        c.execute("CREATE TABLE IF NOT EXISTS system_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_name TEXT NOT NULL, payload TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        c.commit()
def record_event(event_name: str, payload: dict | None = None) -> None:
    """Grava um evento do sistema em system_events (auditoria — 'registrar tudo que foi executado')."""
    with get_connection() as c:
        c.execute("INSERT INTO system_events (event_name, payload) VALUES (?, ?)", (event_name, json.dumps(payload) if payload is not None else None))
        c.commit()
