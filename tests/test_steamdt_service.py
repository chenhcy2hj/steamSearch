from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.storage.db import Database
from app.storage.migrations import run_migrations
from app.storage.repositories.items import ItemRepository
from app.steamdt.dto import SteamDTBaseItem, SteamDTPlatformInfo
from app.steamdt.service import SteamDTService


class FakeSteamDTClient:
    async def fetch_base_items(self) -> list[SteamDTBaseItem]:
        return [
            SteamDTBaseItem(
                name="皇后",
                market_hash_name="AK-47 | The Empress (Field-Tested)",
                platform_list=(SteamDTPlatformInfo(name="BUFF", item_id="123"),),
            ),
            SteamDTBaseItem(
                name="二西莫夫",
                market_hash_name="AWP | Asiimov (Battle-Scarred)",
                platform_list=(SteamDTPlatformInfo(name="Steam", item_id="456"),),
            ),
        ]


class SteamDTServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.connect()
        run_migrations(self.database)
        self.repository = ItemRepository(self.database)

    async def asyncTearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    async def test_sync_base_items_writes_searchable_items(self) -> None:
        service = SteamDTService(FakeSteamDTClient(), self.repository)

        count = await service.sync_base_items()
        search_results = self.repository.search("Asiimov")
        aliases = self.repository.aliases_for_item(search_results[0].id)

        self.assertEqual(count, 2)
        self.assertEqual(search_results[0].market_hash_name, "AWP | Asiimov (Battle-Scarred)")
        self.assertEqual(aliases[0].source, "Steam")
        self.assertEqual(aliases[0].source_item_id, "456")


if __name__ == "__main__":
    unittest.main()

