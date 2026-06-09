from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import AppSettings, load_settings
from app.core.logger import configure_logging, get_logger
from app.storage.db import Database
from app.storage.migrations import run_migrations


@dataclass(frozen=True)
class AppContext:
    settings: AppSettings
    config_path: Path
    database: Database


def bootstrap_app() -> AppContext:
    settings, config_path = load_settings()
    _ensure_runtime_paths(settings)
    configure_logging(settings.app.log_level, settings.app.log_path)

    logger = get_logger(__name__)
    logger.info("Starting SteamSearch bootstrap")

    database = Database(settings.app.database_path)
    database.connect()
    run_migrations(database)

    logger.info("SteamSearch bootstrap finished")
    return AppContext(settings=settings, config_path=config_path, database=database)


def _ensure_runtime_paths(settings: AppSettings) -> None:
    settings.app.database_path.parent.mkdir(parents=True, exist_ok=True)
    settings.app.log_path.parent.mkdir(parents=True, exist_ok=True)

