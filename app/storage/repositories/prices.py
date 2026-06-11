from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from sqlite3 import Row
from typing import Any

from app.buff.dto import BuffListingSummary
from app.storage.db import Database
from app.storage.models import PriceSnapshotRecord
from app.steamdt.dto import SteamDTPlatformPrice


class PriceSnapshotRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save_steamdt_prices(
        self,
        item_id: int,
        prices: list[SteamDTPlatformPrice],
    ) -> str:
        captured_at = _utc_now()
        for price in prices:
            self.database.connection.execute(
                """
                INSERT INTO price_snapshots (
                  item_id,
                  source,
                  sell_price,
                  lowest_price,
                  sell_count,
                  raw_json,
                  captured_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    f"steamdt:{price.platform}",
                    str(price.sell_price),
                    str(price.sell_price),
                    price.sell_count,
                    _json_dump(
                        {
                            "platform": price.platform,
                            "platform_item_id": price.platform_item_id,
                            "bidding_price": str(price.bidding_price),
                            "bidding_count": price.bidding_count,
                            "update_time": price.update_time,
                        }
                    ),
                    captured_at,
                ),
            )
        self.database.connection.commit()
        return captured_at

    def save_buff_summary(self, item_id: int, summary: BuffListingSummary) -> str:
        captured_at = _utc_now()
        self.database.execute(
            """
            INSERT INTO price_snapshots (
              item_id,
              source,
              buy_price,
              lowest_price,
              sell_count,
              raw_json,
              captured_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                "buff",
                str(summary.lowest_price),
                str(summary.lowest_price),
                summary.sell_count,
                _json_dump({"goods_id": summary.goods_id, "market_hash_name": summary.market_hash_name}),
                captured_at,
            ),
        )
        return captured_at

    def latest_for_item(self, item_id: int, limit: int = 20) -> list[PriceSnapshotRecord]:
        rows = self.database.connection.execute(
            """
            SELECT *
            FROM price_snapshots
            WHERE item_id = ?
            ORDER BY captured_at DESC, id DESC
            LIMIT ?
            """,
            (item_id, limit),
        ).fetchall()
        return [_to_record(row) for row in rows]


def _to_record(row: Row) -> PriceSnapshotRecord:
    return PriceSnapshotRecord(
        id=int(row["id"]),
        item_id=int(row["item_id"]),
        source=str(row["source"]),
        buy_price=_decimal_or_none(row["buy_price"]),
        sell_price=_decimal_or_none(row["sell_price"]),
        lowest_price=_decimal_or_none(row["lowest_price"]),
        sell_count=_int_or_none(row["sell_count"]),
        currency=str(row["currency"]),
        raw_json=row["raw_json"],
        captured_at=str(row["captured_at"]),
    )


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _json_dump(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
