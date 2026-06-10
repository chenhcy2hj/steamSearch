from __future__ import annotations

from dataclasses import dataclass


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

