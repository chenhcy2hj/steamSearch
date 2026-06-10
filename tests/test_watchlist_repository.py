from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.storage.db import Database
from app.storage.migrations import run_migrations
from app.storage.models import ItemInput, WatchlistInput
from app.storage.repositories.items import ItemRepository
from app.storage.repositories.watchlist import WatchlistRepository


class WatchlistRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.connect()
        run_migrations(self.database)
        self.items = ItemRepository(self.database)
        self.watchlist = WatchlistRepository(self.database)
        self.item_id = self.items.upsert(
            ItemInput(
                market_hash_name="AK-47 | The Empress (Field-Tested)",
                name_cn="皇后",
            )
        )

    def tearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    def test_add_lists_and_deduplicates_item(self) -> None:
        first = self.watchlist.add(WatchlistInput(item_id=self.item_id))
        second = self.watchlist.add(WatchlistInput(item_id=self.item_id))
        records = self.watchlist.list_all()

        self.assertEqual(first, second)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].market_hash_name, "AK-47 | The Empress (Field-Tested)")

    def test_set_enabled_and_delete(self) -> None:
        watchlist_id = self.watchlist.add(WatchlistInput(item_id=self.item_id))

        self.assertTrue(self.watchlist.set_enabled(watchlist_id, False))
        self.assertFalse(self.watchlist.list_all()[0].enabled)
        self.assertTrue(self.watchlist.delete(watchlist_id))
        self.assertEqual(self.watchlist.list_all(), [])


if __name__ == "__main__":
    unittest.main()
