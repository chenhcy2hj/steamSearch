from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping


@dataclass(frozen=True)
class SteamDTPlatformInfo:
    name: str
    item_id: str


@dataclass(frozen=True)
class SteamDTBaseItem:
    name: str
    market_hash_name: str
    platform_list: tuple[SteamDTPlatformInfo, ...]


@dataclass(frozen=True)
class SteamDTPlatformPrice:
    platform: str
    platform_item_id: str
    sell_price: Decimal
    sell_count: int
    bidding_price: Decimal
    bidding_count: int
    update_time: int


@dataclass(frozen=True)
class SteamDTBatchPrice:
    market_hash_name: str
    data_list: tuple[SteamDTPlatformPrice, ...]


@dataclass(frozen=True)
class SteamDTKlinePoint:
    raw: Mapping[str, Any]

