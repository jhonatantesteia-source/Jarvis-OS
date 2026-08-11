import sys
from pathlib import Path
from loguru import logger
def configure_logging(level: str = "INFO") -> None:
    Path("logs").mkdir(exist_ok=True)
    logger.remove(); logger.add(sys.stderr, level=level); logger.add("logs/jarvis.log", level=level, rotation="10 MB", retention="14 days", encoding="utf-8")
