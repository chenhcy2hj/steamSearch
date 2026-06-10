from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

from app.core.constants import DEFAULT_CONFIG_PATH, DEFAULT_DATABASE_PATH, DEFAULT_LOG_PATH


@dataclass(frozen=True)
class SteamDTSettings:
    api_key: str = ""
    base_url: str = "https://open.steamdt.com"
    base_sync_ttl_hours: int = 24
    price_cache_ttl_seconds: int = 60
    kline_cache_ttl_seconds: int = 1800


@dataclass(frozen=True)
class BuffSettings:
    enabled: bool = False
    cookie: str = ""
    min_interval_seconds: int = 6
    max_interval_seconds: int = 12
    cache_ttl_seconds: int = 600
    max_items_per_scan: int = 30


@dataclass(frozen=True)
class MarketSettings:
    steam_fee_rate: float = 0.15
    wallet_discount_rate: float = 1.0
    min_profit: float = 1.0
    min_roi: float = 0.03


@dataclass(frozen=True)
class RuntimeSettings:
    log_level: str = "INFO"
    theme: str = "system"
    database_path: Path = DEFAULT_DATABASE_PATH
    log_path: Path = DEFAULT_LOG_PATH


@dataclass(frozen=True)
class AppSettings:
    steamdt: SteamDTSettings
    buff: BuffSettings
    market: MarketSettings
    app: RuntimeSettings


def load_settings(config_path: Path = DEFAULT_CONFIG_PATH) -> Tuple[AppSettings, Path]:
    raw = _load_config_file(config_path)
    _apply_environment_overrides(raw)
    settings = AppSettings(
        steamdt=SteamDTSettings(**raw.get("steamdt", {})),
        buff=BuffSettings(**raw.get("buff", {})),
        market=MarketSettings(**raw.get("market", {})),
        app=_build_runtime_settings(raw.get("app", {})),
    )
    return settings, config_path


def _build_runtime_settings(values: Dict[str, Any]) -> RuntimeSettings:
    database_path = _resolve_project_path(values.get("database_path"), DEFAULT_DATABASE_PATH)
    log_path = _resolve_project_path(values.get("log_path"), DEFAULT_LOG_PATH)
    return RuntimeSettings(
        log_level=str(values.get("log_level", "INFO")),
        theme=str(values.get("theme", "system")),
        database_path=database_path,
        log_path=log_path,
    )


def _resolve_project_path(value: Any, default: Path) -> Path:
    if not value:
        return default
    path = Path(str(value))
    if path.is_absolute():
        return path
    return default.parents[1] / path


def _load_config_file(config_path: Path) -> Dict[str, Dict[str, Any]]:
    if not config_path.exists():
        return {}

    try:
        import tomllib  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        return _parse_simple_toml(config_path.read_text(encoding="utf-8"))

    with config_path.open("rb") as file:
        return tomllib.load(file)


def _parse_simple_toml(content: str) -> Dict[str, Dict[str, Any]]:
    data: Dict[str, Dict[str, Any]] = {}
    section: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            data.setdefault(section, {})
            continue
        if section is None or "=" not in line:
            continue

        key, value = line.split("=", 1)
        data[section][key.strip()] = _parse_scalar(value.strip())

    return data


def _parse_scalar(value: str) -> Any:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _apply_environment_overrides(raw: Dict[str, Dict[str, Any]]) -> None:
    steamdt_api_key = os.environ.get("STEAMDT_API_KEY")
    if steamdt_api_key:
        raw.setdefault("steamdt", {})["api_key"] = steamdt_api_key

    steamdt_base_url = os.environ.get("STEAMDT_BASE_URL")
    if steamdt_base_url:
        raw.setdefault("steamdt", {})["base_url"] = steamdt_base_url
