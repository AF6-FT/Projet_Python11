"""Configuration des fichiers de logs du projet."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
LOG_DIR = PROJECT_DIR / "logs"
LOG_FORMAT = "%(asctime)s|%(levelname)s|%(name)s|%(message)s"

_LOG_FILES = {
    "pipeline.ingestion": "ingestion.log",
    "pipeline.processing": "processing.log",
    "pipeline.orchestrator": "pipeline.log",
    "storage": "storage.log",
    "serving": "serving.log",
    "main": "main.log",
}


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger qui écrit dans le fichier de son module."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_name = _LOG_FILES.get(name)
    if log_name is None:
        parent_name = name.rsplit(".", 1)[0]
        log_name = _LOG_FILES.get(parent_name, f"{name.replace('.', '_')}.log")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        LOG_DIR / log_name,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
