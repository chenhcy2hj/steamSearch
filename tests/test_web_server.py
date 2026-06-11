from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from app.core.config import AppSettings, BuffSettings, MarketSettings, RuntimeSettings, SteamDTSettings
from app.bootstrap import AppContext
from app.buff.dto import BuffListingSummary
from app.market.scanner import RadarCandidate, RadarResult
from app.storage.db import Database
from app.storage.migrations import run_migrations
from app.storage.models import WatchlistInput
from app.storage.repositories.items import ItemRepository
from app.storage.repositories.watchlist import WatchlistRepository
from app.steamdt.dto import SteamDTPlatformPrice
from app.steamdt.dto import SteamDTBatchPrice
from app.ui.web_server import (
    confirm_radar_candidates_with_buff,
    build_steamdt_radar_candidates,
    build_demo_quote,
    build_steamdt_quote,
    find_available_port,
    _radar_to_json,
    seed_demo_items_if_empty,
)


class FakeBuffService:
    def __init__(self) -> None:
        self.requests: list[str] = []

    async def fetch_listing_summary(
        self,
        market_hash_name: str,
        goods_id: str | None = None,
    ) -> BuffListingSummary:
        self.requests.append(market_hash_name)
        if market_hash_name == "Fail":
            raise RuntimeError("buff failed")
        return BuffListingSummary(
            goods_id="buff-1",
            market_hash_name=market_hash_name,
            lowest_price=Decimal("88"),
            sell_count=5,
        )


class WebServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.database = Database(root / "test.db")
        self.database.connect()
        run_migrations(self.database)
        self.repository = ItemRepository(self.database)
        self.watchlist = WatchlistRepository(self.database)
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

    def test_build_demo_quote_uses_buff_price_when_available(self) -> None:
        seed_demo_items_if_empty(self.repository)
        item = self.repository.search("Empress")[0]

        quote = build_demo_quote(
            item,
            self.context.settings.market,
            BuffListingSummary(
                goods_id="buff-1",
                market_hash_name=item.market_hash_name,
                lowest_price=100,
                sell_count=7,
            ),
        )

        self.assertEqual(quote["sources"]["buy"]["name"], "BUFF 实时最低挂单")
        self.assertEqual(quote["sources"]["buy"]["price"], "¥100.00")
        self.assertIn("BUFF", quote["warning"])

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
            captured_at="2026-06-11T10:00:00+00:00",
        )

        self.assertTrue(quote["live"])
        self.assertEqual(quote["captured_at"], "2026-06-11T10:00:00+00:00")
        self.assertEqual(quote["sources"]["buy"]["price"], "¥100.00")
        self.assertEqual(quote["sources"]["sell"]["price"], "¥150.00")
        self.assertEqual(quote["platform_prices"][0]["platform"], "buff")
        self.assertIn("%", quote["profit"]["roi"])

    def test_build_steamdt_quote_keeps_result_when_buff_fails(self) -> None:
        seed_demo_items_if_empty(self.repository)
        item = self.repository.search("Empress")[0]

        quote = build_steamdt_quote(
            item,
            [
                SteamDTPlatformPrice(
                    platform="steam",
                    platform_item_id="steam-1",
                    sell_price=150,
                    sell_count=5,
                    bidding_price=130,
                    bidding_count=2,
                    update_time=1710000001,
                )
            ],
            self.context.settings.market,
            RuntimeError("cookie invalid"),
        )

        self.assertTrue(quote["live"])
        self.assertIn("BUFF 增强失败", quote["warning"])

    def test_watchlist_repository_works_with_seeded_items(self) -> None:
        seed_demo_items_if_empty(self.repository)
        item = self.repository.search("Empress")[0]

        watchlist_id = self.watchlist.add(WatchlistInput(item_id=item.id))

        records = self.watchlist.list_all()

        self.assertEqual(records[0].id, watchlist_id)
        self.assertEqual(records[0].market_hash_name, item.market_hash_name)

    def test_find_available_port_skips_busy_port(self) -> None:
        def fake_checker(host: str, port: int) -> bool:
            return port != 8765

        selected = find_available_port("127.0.0.1", 8765, max_attempts=3, port_checker=fake_checker)

        self.assertEqual(selected, 8766)

    def test_radar_to_json_formats_values(self) -> None:
        payload = _radar_to_json(
            RadarResult(
                item_id=1,
                market_hash_name="AK-47 | The Empress (Field-Tested)",
                name_cn="皇后",
                category="rifle",
                buy_price=100,
                sell_price=150,
                net_sell_price=127.5,
                profit=27.5,
                roi=0.275,
                spread=0.5,
                risk_score=95,
            )
        )

        self.assertEqual(payload["profit"], "¥27.50")
        self.assertEqual(payload["roi"], "27.50%")

    def test_build_steamdt_radar_candidates_uses_lowest_buy_and_steam_sell_price(self) -> None:
        seed_demo_items_if_empty(self.repository)
        item = self.repository.search("Empress")[0]

        candidates = build_steamdt_radar_candidates(
            [item],
            [
                SteamDTBatchPrice(
                    market_hash_name=item.market_hash_name,
                    data_list=(
                        SteamDTPlatformPrice(
                            platform="BUFF",
                            platform_item_id="buff-1",
                            sell_price=100,
                            sell_count=10,
                            bidding_price=95,
                            bidding_count=2,
                            update_time=1710000000,
                        ),
                        SteamDTPlatformPrice(
                            platform="Steam",
                            platform_item_id="steam-1",
                            sell_price=150,
                            sell_count=4,
                            bidding_price=130,
                            bidding_count=1,
                            update_time=1710000001,
                        ),
                    ),
                )
            ],
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].buy_price, 100)
        self.assertEqual(candidates[0].sell_price, 150)

    def test_confirm_radar_candidates_with_buff_replaces_buy_price_and_keeps_failures(self) -> None:
        buff = FakeBuffService()
        candidates = [
            RadarCandidate(
                item_id=1,
                market_hash_name="OK",
                name_cn=None,
                category=None,
                buy_price=Decimal("100"),
                sell_price=Decimal("150"),
            ),
            RadarCandidate(
                item_id=2,
                market_hash_name="Fail",
                name_cn=None,
                category=None,
                buy_price=Decimal("90"),
                sell_price=Decimal("140"),
            ),
        ]

        confirmed, stats = self.run_async(
            confirm_radar_candidates_with_buff(candidates, buff, max_items=2)
        )

        self.assertEqual(stats["confirmed"], 1)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(confirmed[0].buy_price, Decimal("88"))
        self.assertEqual(confirmed[1].buy_price, Decimal("90"))
        self.assertEqual(buff.requests, ["OK", "Fail"])

    def run_async(self, awaitable):
        import asyncio

        return asyncio.run(awaitable)


if __name__ == "__main__":
    unittest.main()
