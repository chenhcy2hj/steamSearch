from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple

from app.core.logger import get_logger
from app.storage.db import Database

logger = get_logger(__name__)

Migration = Tuple[int, str]


MIGRATIONS: List[Migration] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_version (
          version INTEGER NOT NULL,
          applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS items (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          steamdt_item_id TEXT UNIQUE,
          market_hash_name TEXT NOT NULL UNIQUE,
          name_cn TEXT,
          name_en TEXT,
          category TEXT,
          rarity TEXT,
          icon_url TEXT,
          tradable INTEGER DEFAULT 1,
          updated_at TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS items_fts
        USING fts5(
          market_hash_name,
          name_cn,
          name_en,
          category,
          content='items',
          content_rowid='id'
        );

        CREATE TABLE IF NOT EXISTS item_aliases (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          item_id INTEGER NOT NULL,
          source TEXT NOT NULL,
          source_item_id TEXT,
          source_name TEXT,
          updated_at TEXT NOT NULL,
          UNIQUE(source, source_item_id),
          FOREIGN KEY(item_id) REFERENCES items(id)
        );

        CREATE TABLE IF NOT EXISTS price_snapshots (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          item_id INTEGER NOT NULL,
          source TEXT NOT NULL,
          buy_price REAL,
          sell_price REAL,
          lowest_price REAL,
          sell_count INTEGER,
          currency TEXT NOT NULL DEFAULT 'CNY',
          raw_json TEXT,
          captured_at TEXT NOT NULL,
          FOREIGN KEY(item_id) REFERENCES items(id)
        );

        CREATE INDEX IF NOT EXISTS idx_price_snapshots_item_source_time
        ON price_snapshots(item_id, source, captured_at);

        CREATE TABLE IF NOT EXISTS watchlist (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          item_id INTEGER NOT NULL,
          target_buy_price REAL,
          target_roi REAL,
          enabled INTEGER NOT NULL DEFAULT 1,
          note TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(item_id) REFERENCES items(id)
        );

        CREATE TABLE IF NOT EXISTS scan_results (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          item_id INTEGER NOT NULL,
          buy_source TEXT NOT NULL,
          sell_source TEXT NOT NULL,
          buy_price REAL NOT NULL,
          sell_price REAL NOT NULL,
          net_sell_price REAL NOT NULL,
          profit REAL NOT NULL,
          roi REAL NOT NULL,
          risk_score REAL,
          captured_at TEXT NOT NULL,
          FOREIGN KEY(item_id) REFERENCES items(id)
        );

        CREATE TABLE IF NOT EXISTS source_health (
          source TEXT PRIMARY KEY,
          enabled INTEGER NOT NULL DEFAULT 1,
          last_success_at TEXT,
          last_error TEXT,
          cooldown_until TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        """,
    )
]


def run_migrations(database: Database) -> None:
    _ensure_schema_version_table(database)
    current_version = _current_version(database)

    for version, script in MIGRATIONS:
        if version <= current_version:
            continue
        logger.info("Applying database migration %s", version)
        database.execute_script(script)
        database.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (version, datetime.now(timezone.utc).isoformat()),
        )


def _ensure_schema_version_table(database: Database) -> None:
    database.execute_script(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
          version INTEGER NOT NULL,
          applied_at TEXT NOT NULL
        );
        """
    )


def _current_version(database: Database) -> int:
    row = database.connection.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()
    if row is None or row["version"] is None:
        return 0
    return int(row["version"])

