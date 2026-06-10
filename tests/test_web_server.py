from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.config import AppSettings, BuffSettings, MarketSettings, RuntimeSettings, SteamDTSettings
from app.bootstrap import AppContext
from app.storage.db import Database
from app.storage.migrations import run_migrations
from app.storage.repositories.items import ItemRepository
from app.steamdt.dto import SteamDTPlatformPrice
from app.ui.web_server import build_demo_quote, build_steamdt_quote, seed_demo_items_if_empty


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

    def test_build_steamdt_quote_contains_platform_prices(self) -> None:
        seed_demo_items_if_empty(self.repository)
        item = self.repository.search("Empress")[0]

        quote = build_steamdt_quote(
            item,
            [
                SteamDTPlatformPrice(
                    platform="buff",
                    platform_item_id="buff-1",
                    sell_price=100,
                    sell_count=9,
                    bidding_price=95,
                    bidding_count=3,
                    update_time=1710000000,
                ),
                SteamDTPlatformPrice(
                    platform="steam",
                    platform_item_id="steam-1",
                    sell_price=150,
                    sell_count=5,
                    bidding_price=130,
                    bidding_count=2,
                    update_time=1710000001,
                ),
            ],
            self.context.settings.market,
        )

        self.assertTrue(quote["live"])
        self.assertEqual(quote["sources"]["buy"]["price"], "¥100.00")
        self.assertEqual(quote["sources"]["sell"]["price"], "¥150.00")
        self.assertEqual(quote["platform_prices"][0]["platform"], "buff")
        self.assertIn("%", quote["profit"]["roi"])


if __name__ == "__main__":
    unittest.main()
