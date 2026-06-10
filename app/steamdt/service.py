from __future__ import annotations

from app.storage.models import ItemAliasInput, ItemInput
from app.storage.repositories.items import ItemRepository
from app.steamdt.client import SteamDTClient
from app.steamdt.dto import SteamDTBaseItem


class SteamDTService:
    def __init__(self, client: SteamDTClient, item_repository: ItemRepository) -> None:
        self.client = client
        self.item_repository = item_repository

    async def sync_base_items(self) -> int:
        base_items = await self.client.fetch_base_items()
        return self.item_repository.upsert_many(_to_item_input(item) for item in base_items)


def _to_item_input(item: SteamDTBaseItem) -> ItemInput:
    return ItemInput(
        market_hash_name=item.market_hash_name,
        name_cn=item.name,
        name_en=_infer_english_name(item.market_hash_name),
        aliases=tuple(
            ItemAliasInput(
                source=platform.name,
                source_item_id=platform.item_id,
                source_name=platform.name,
            )
            for platform in item.platform_list
        ),
    )


def _infer_english_name(market_hash_name: str) -> str:
    if "(" not in market_hash_name:
        return market_hash_name
    return market_hash_name.split("(", 1)[0].strip()

