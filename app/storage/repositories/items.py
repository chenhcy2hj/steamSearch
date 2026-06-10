from __future__ import annotations

import re
from datetime import datetime, timezone
from sqlite3 import Row
from typing import Iterable

from app.storage.db import Database
from app.storage.models import ItemAliasInput, ItemInput, ItemRecord


class ItemRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def upsert_many(self, items: Iterable[ItemInput]) -> int:
        count = 0
        for item in items:
            self.upsert(item)
            count += 1
        self.rebuild_search_index()
        return count

    def upsert(self, item: ItemInput) -> int:
        now = _utc_now()
        connection = self.database.connection
        connection.execute(
            """
            INSERT INTO items (
              steamdt_item_id,
              market_hash_name,
              name_cn,
              name_en,
              category,
              rarity,
              icon_url,
              tradable,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(market_hash_name) DO UPDATE SET
              steamdt_item_id = excluded.steamdt_item_id,
              name_cn = excluded.name_cn,
              name_en = excluded.name_en,
              category = excluded.category,
              rarity = excluded.rarity,
              icon_url = excluded.icon_url,
              tradable = excluded.tradable,
              updated_at = excluded.updated_at
            """,
            (
                item.steamdt_item_id,
                item.market_hash_name,
                item.name_cn,
                item.name_en,
                item.category,
                item.rarity,
                item.icon_url,
                1 if item.tradable else 0,
                now,
            ),
        )
        row = connection.execute(
            "SELECT id FROM items WHERE market_hash_name = ?",
            (item.market_hash_name,),
        ).fetchone()
        item_id = int(row["id"])
        self._upsert_aliases(item_id, item.aliases, now)
        connection.commit()
        return item_id

    def get_by_market_hash_name(self, market_hash_name: str) -> ItemRecord | None:
        row = self.database.connection.execute(
            "SELECT * FROM items WHERE market_hash_name = ?",
            (market_hash_name,),
        ).fetchone()
        if row is None:
            return None
        return _to_item_record(row)

    def search(self, query: str, limit: int = 20) -> list[ItemRecord]:
        cleaned = query.strip()
        if not cleaned:
            return self._list_recent(limit)

        fts_query = _build_fts_query(cleaned)
        rows: list[Row] = []
        if fts_query:
            rows = list(
                self.database.connection.execute(
                    """
                    SELECT items.*
                    FROM items_fts
                    JOIN items ON items.id = items_fts.rowid
                    WHERE items_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_query, limit),
                ).fetchall()
            )

        if not rows:
            rows = self._search_like(cleaned, limit)

        return [_to_item_record(row) for row in rows]

    def rebuild_search_index(self) -> None:
        self.database.connection.execute("INSERT INTO items_fts(items_fts) VALUES('rebuild')")
        self.database.connection.commit()

    def count(self) -> int:
        row = self.database.connection.execute("SELECT COUNT(*) AS total FROM items").fetchone()
        return int(row["total"])

    def aliases_for_item(self, item_id: int) -> list[ItemAliasInput]:
        rows = self.database.connection.execute(
            """
            SELECT source, source_item_id, source_name
            FROM item_aliases
            WHERE item_id = ?
            ORDER BY source, source_item_id
            """,
            (item_id,),
        ).fetchall()
        return [
            ItemAliasInput(
                source=str(row["source"]),
                source_item_id=str(row["source_item_id"]),
                source_name=str(row["source_name"]),
            )
            for row in rows
        ]

    def _upsert_aliases(
        self,
        item_id: int,
        aliases: Iterable[ItemAliasInput],
        updated_at: str,
    ) -> None:
        for alias in aliases:
            if not alias.source or not alias.source_item_id:
                continue
            self.database.connection.execute(
                """
                INSERT INTO item_aliases (
                  item_id,
                  source,
                  source_item_id,
                  source_name,
                  updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source, source_item_id) DO UPDATE SET
                  item_id = excluded.item_id,
                  source_name = excluded.source_name,
                  updated_at = excluded.updated_at
                """,
                (item_id, alias.source, alias.source_item_id, alias.source_name, updated_at),
            )

    def _list_recent(self, limit: int) -> list[ItemRecord]:
        rows = self.database.connection.execute(
            "SELECT * FROM items ORDER BY updated_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_to_item_record(row) for row in rows]

    def _search_like(self, query: str, limit: int) -> list[Row]:
        pattern = f"%{query}%"
        return list(
            self.database.connection.execute(
                """
                SELECT *
                FROM items
                WHERE market_hash_name LIKE ?
                   OR name_cn LIKE ?
                   OR name_en LIKE ?
                   OR category LIKE ?
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (pattern, pattern, pattern, pattern, limit),
            ).fetchall()
        )


def _to_item_record(row: Row) -> ItemRecord:
    return ItemRecord(
        id=int(row["id"]),
        market_hash_name=str(row["market_hash_name"]),
        steamdt_item_id=row["steamdt_item_id"],
        name_cn=row["name_cn"],
        name_en=row["name_en"],
        category=row["category"],
        rarity=row["rarity"],
        icon_url=row["icon_url"],
        tradable=bool(row["tradable"]),
        updated_at=str(row["updated_at"]),
    )


def _build_fts_query(query: str) -> str:
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", query, flags=re.UNICODE)
    return " ".join(f"{token}*" for token in tokens)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

