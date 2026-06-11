from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ItemAliasInput:
    source: str
    source_item_id: str
    source_name: str


@dataclass(frozen=True)
class ItemInput:
    market_hash_name: str
    steamdt_item_id: str | None = None
    name_cn: str | None = None
    name_en: str | None = None
    category: str | None = None
    rarity: str | None = None
    icon_url: str | None = None
    tradable: bool = True
    aliases: tuple[ItemAliasInput, ...] = ()


@dataclass(frozen=True)
class ItemRecord:
    id: int
    market_hash_name: str
    steamdt_item_id: str | None
    name_cn: str | None
    name_en: str | None
    category: str | None
    rarity: str | None
    icon_url: str | None
    tradable: bool
    updated_at: str


@dataclass(frozen=True)
class WatchlistInput:
    item_id: int
    target_buy_price: float | None = None
    target_roi: float | None = None
    enabled: bool = True
    note: str | None = None


@dataclass(frozen=True)
class WatchlistRecord:
    id: int
    item_id: int
    market_hash_name: str
    name_cn: str | None
    target_buy_price: float | None
    target_roi: float | None
    enabled: bool
    note: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class PriceSnapshotRecord:
    id: int
    item_id: int
    source: str
    buy_price: Decimal | None
    sell_price: Decimal | None
    lowest_price: Decimal | None
    sell_count: int | None
    currency: str
    raw_json: str | None
    captured_at: str
