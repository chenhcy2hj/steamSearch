from __future__ import annotations

from datetime import datetime, timezone
from sqlite3 import Row

from app.storage.db import Database
from app.storage.models import WatchlistInput, WatchlistRecord


class WatchlistRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def add(self, item: WatchlistInput) -> int:
        existing = self._find_by_item_id(item.item_id)
        if existing is not None:
            self.set_enabled(existing.id, True)
            return existing.id

        now = _utc_now()
        cursor = self.database.execute(
            """
            INSERT INTO watchlist (
              item_id,
              target_buy_price,
              target_roi,
              enabled,
              note,
              created_at,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.item_id,
                item.target_buy_price,
                item.target_roi,
                1 if item.enabled else 0,
                item.note,
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)

    def list_all(self) -> list[WatchlistRecord]:
        rows = self.database.connection.execute(
            """
            SELECT
              watchlist.id,
              watchlist.item_id,
              items.market_hash_name,
              items.name_cn,
              watchlist.target_buy_price,
              watchlist.target_roi,
              watchlist.enabled,
              watchlist.note,
              watchlist.created_at,
              watchlist.updated_at
            FROM watchlist
            JOIN items ON items.id = watchlist.item_id
            ORDER BY watchlist.updated_at DESC, watchlist.id DESC
            """
        ).fetchall()
        return [_to_watchlist_record(row) for row in rows]

    def set_enabled(self, watchlist_id: int, enabled: bool) -> bool:
        cursor = self.database.execute(
            """
            UPDATE watchlist
            SET enabled = ?, updated_at = ?
            WHERE id = ?
            """,
            (1 if enabled else 0, _utc_now(), watchlist_id),
        )
        return cursor.rowcount > 0

    def delete(self, watchlist_id: int) -> bool:
        cursor = self.database.execute("DELETE FROM watchlist WHERE id = ?", (watchlist_id,))
        return cursor.rowcount > 0

    def _find_by_item_id(self, item_id: int) -> WatchlistRecord | None:
        row = self.database.connection.execute(
            """
            SELECT
              watchlist.id,
              watchlist.item_id,
              items.market_hash_name,
              items.name_cn,
              watchlist.target_buy_price,
              watchlist.target_roi,
              watchlist.enabled,
              watchlist.note,
              watchlist.created_at,
              watchlist.updated_at
            FROM watchlist
            JOIN items ON items.id = watchlist.item_id
            WHERE watchlist.item_id = ?
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        return _to_watchlist_record(row)


def _to_watchlist_record(row: Row) -> WatchlistRecord:
    return WatchlistRecord(
        id=int(row["id"]),
        item_id=int(row["item_id"]),
        market_hash_name=str(row["market_hash_name"]),
        name_cn=row["name_cn"],
        target_buy_price=row["target_buy_price"],
        target_roi=row["target_roi"],
        enabled=bool(row["enabled"]),
        note=row["note"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
