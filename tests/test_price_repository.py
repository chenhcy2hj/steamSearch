from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from app.storage.db import Database
from app.storage.migrations import run_migrations
from app.storage.models import ItemInput
from app.storage.repositories.items import ItemRepository
from app.storage.repositories.prices import PriceSnapshotRepository
from app.steamdt.dto import SteamDTPlatformPrice


class PriceSnapshotRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.connect()
        run_migrations(self.database)
        self.items = ItemRepository(self.database)
        self.prices = PriceSnapshotRepository(self.database)
        self.item_id = self.items.upsert(ItemInput(market_hash_name="AK-47 | Redline (Field-Tested)"))

    def tearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    def test_saves_steamdt_platform_snapshots_with_capture_time(self) -> None:
        captured_at = self.prices.save_steamdt_prices(
            self.item_id,
            [
                SteamDTPlatformPrice(
                    platform="BUFF",
                    platform_item_id="buff-1",
                    sell_price=Decimal("100.5"),
                    sell_count=9,
                    bidding_price=Decimal("95"),
                    bidding_count=3,
                    update_time=1710000000,
                )
            ],
        )

        latest = self.prices.latest_for_item(self.item_id)

        self.assertEqual(len(latest), 1)
        self.assertEqual(latest[0].source, "steamdt:BUFF")
        self.assertEqual(latest[0].sell_price, Decimal("100.5"))
        self.assertEqual(latest[0].sell_count, 9)
        self.assertEqual(latest[0].captured_at, captured_at)


if __name__ == "__main__":
    unittest.main()
