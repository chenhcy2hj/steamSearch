from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.storage.db import Database
from app.storage.migrations import run_migrations
from app.storage.models import ItemAliasInput, ItemInput
from app.storage.repositories.items import ItemRepository


class ItemRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.connect()
        run_migrations(self.database)
        self.repository = ItemRepository(self.database)

    def tearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    def test_upserts_items_and_aliases(self) -> None:
        item_id = self.repository.upsert(
            ItemInput(
                market_hash_name="AK-47 | The Empress (Field-Tested)",
                name_cn="皇后",
                name_en="AK-47 | The Empress",
                category="rifle",
                aliases=(
                    ItemAliasInput(source="BUFF", source_item_id="123", source_name="BUFF"),
                ),
            )
        )
        self.repository.rebuild_search_index()

        item = self.repository.get_by_market_hash_name("AK-47 | The Empress (Field-Tested)")
        aliases = self.repository.aliases_for_item(item_id)

        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.name_cn, "皇后")
        self.assertEqual(aliases[0].source, "BUFF")
        self.assertEqual(aliases[0].source_item_id, "123")

    def test_searches_by_english_and_chinese_names(self) -> None:
        self.repository.upsert_many(
            [
                ItemInput(
                    market_hash_name="AK-47 | The Empress (Field-Tested)",
                    name_cn="皇后",
                    name_en="AK-47 | The Empress",
                    category="rifle",
                ),
                ItemInput(
                    market_hash_name="AWP | Asiimov (Battle-Scarred)",
                    name_cn="二西莫夫",
                    name_en="AWP | Asiimov",
                    category="sniper",
                ),
            ]
        )

        english_results = self.repository.search("AK Empress")
        chinese_results = self.repository.search("皇后")

        self.assertEqual(english_results[0].market_hash_name, "AK-47 | The Empress (Field-Tested)")
        self.assertEqual(chinese_results[0].market_hash_name, "AK-47 | The Empress (Field-Tested)")

    def test_upsert_many_rebuilds_search_index(self) -> None:
        count = self.repository.upsert_many(
            [
                ItemInput(
                    market_hash_name="M4A1-S | Printstream (Minimal Wear)",
                    name_cn="印花集",
                    name_en="M4A1-S | Printstream",
                    category="rifle",
                )
            ]
        )

        results = self.repository.search("Printstream")

        self.assertEqual(count, 1)
        self.assertEqual(results[0].market_hash_name, "M4A1-S | Printstream (Minimal Wear)")


if __name__ == "__main__":
    unittest.main()

