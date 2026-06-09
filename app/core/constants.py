from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.local.toml"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config" / "config.example.toml"
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "steamsearch.db"
DEFAULT_LOG_PATH = PROJECT_ROOT / "logs" / "steamsearch.log"

