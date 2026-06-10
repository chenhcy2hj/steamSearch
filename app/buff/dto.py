from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BuffGoods:
    goods_id: str
    market_hash_name: str
    name: str


@dataclass(frozen=True)
class BuffListingSummary:
    goods_id: str
    market_hash_name: str
    lowest_price: Decimal
    sell_count: int | None
    source: str = "buff"

