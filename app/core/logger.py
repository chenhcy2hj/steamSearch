from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(level: str, log_path: Path) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

