from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.config import AppSettings, BuffSettings, MarketSettings, RuntimeSettings, SteamDTSettings
from app.bootstrap import AppContext
from app.storage.db import Database
from app.storage.migrations import run_migrations
from app.storage.repositories.items import ItemRepository
from app.ui.web_server import build_demo_quote, seed_demo_items_if_empty


class WebServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.database = Database(root / "test.db")
        self.database.connect()
        run_migrations(self.database)
        self.repository = ItemRepository(self.database)
        self.context = AppContext(
            settings=AppSettings(
                steamdt=SteamDTSettings(),
                buff=BuffSettings(),
                market=MarketSettings(),
                app=RuntimeSettings(database_path=root / "test.db", log_path=root / "test.log"),
            ),
            config_path=root / "config.toml",
            database=self.database,
        )

    def tearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    def test_seed_demo_items_only_when_empty(self) -> None:
        seed_demo_items_if_empty(self.repository)
        first_count = self.repository.count()
        seed_demo_items_if_empty(self.repository)

        self.assertGreaterEqual(first_count, 4)
        self.assertEqual(self.repository.count(), first_count)

    def test_build_demo_quote_contains_profit(self) -> None:
        seed_demo_items_if_empty(self.repository)
        item = self.repository.search("Empress")[0]

        quote = build_demo_quote(item, self.context.settings.market)

        self.assertEqual(quote["item"]["market_hash_name"], item.market_hash_name)
        self.assertIn("BUFF", quote["sources"]["buy"]["name"])
        self.assertIn("¥", quote["profit"]["profit"])
        self.assertIn("%", quote["profit"]["roi"])


if __name__ == "__main__":
    unittest.main()

