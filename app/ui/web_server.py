from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from decimal import Decimal
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.bootstrap import AppContext, bootstrap_app
from app.market.calculator import ProfitCalculator, quantize_money, quantize_percent
from app.storage.models import ItemAliasInput, ItemInput, ItemRecord
from app.storage.repositories.items import ItemRepository
from app.steamdt.client import SteamDTClient
from app.steamdt.dto import SteamDTPlatformPrice
from app.steamdt.service import SteamDTService
from app.ui.pages.browser import render_browser_page


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SteamSearch lightweight browser UI.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    parser.add_argument("--no-demo-data", action="store_true")
    args = parser.parse_args()

    context = bootstrap_app()
    item_repository = ItemRepository(context.database)
    if not args.no_demo_data:
        seed_demo_items_if_empty(item_repository)

    steamdt_client = build_steamdt_client(context)
    server = build_server(args.host, args.port, context, item_repository, steamdt_client)
    print(f"SteamSearch Browser running at http://{args.host}:{args.port}")
    if steamdt_client is None:
        print("SteamDT live API disabled. Set STEAMDT_API_KEY or config/config.local.toml.")
    else:
        print("SteamDT live API enabled.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SteamSearch Browser.")
    finally:
        context.database.close()
        server.server_close()


def build_server(
    host: str,
    port: int,
    context: AppContext,
    item_repository: ItemRepository,
    steamdt_client: SteamDTClient | None = None,
) -> HTTPServer:
    class SteamSearchHandler(BrowserRequestHandler):
        app_context = context
        repository = item_repository
        steamdt = steamdt_client

    return HTTPServer((host, port), SteamSearchHandler)


class BrowserRequestHandler(BaseHTTPRequestHandler):
    app_context: AppContext
    repository: ItemRepository
    steamdt: SteamDTClient | None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(render_browser_page())
            return
        if parsed.path == "/api/search":
            self._handle_search(parse_qs(parsed.query))
            return
        if parsed.path == "/api/quote":
            self._handle_quote(parse_qs(parsed.query))
            return
        if parsed.path == "/api/sync/steamdt/base":
            self._handle_sync_steamdt_base()
            return
        if parsed.path == "/api/source-status":
            self._send_json(
                {
                    "steamdt": {
                        "enabled": self.steamdt is not None,
                        "base_url": self.app_context.settings.steamdt.base_url,
                    }
                }
            )
            return
        if parsed.path == "/health":
            self._send_json({"ok": True})
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle_search(self, query: dict[str, list[str]]) -> None:
        keyword = _first(query, "q", "")
        limit = _parse_int(_first(query, "limit", "20"), 20)
        items = self.repository.search(keyword, limit=limit)
        self._send_json({"items": [_item_to_json(item) for item in items]})

    def _handle_quote(self, query: dict[str, list[str]]) -> None:
        market_hash_name = _first(query, "market_hash_name", "")
        item = self.repository.get_by_market_hash_name(market_hash_name)
        if item is None:
            self._send_json({"error": "item not found"}, status=HTTPStatus.NOT_FOUND)
            return
        if self.steamdt is None:
            self._send_json(build_demo_quote(item, self.app_context.settings.market))
            return

        try:
            prices = asyncio.run(self.steamdt.fetch_single_price(item.market_hash_name))
        except Exception as error:
            self._send_json(
                {
                    "error": "SteamDT request failed",
                    "detail": str(error),
                    "fallback": build_demo_quote(item, self.app_context.settings.market),
                },
                status=HTTPStatus.BAD_GATEWAY,
            )
            return

        self._send_json(build_steamdt_quote(item, prices, self.app_context.settings.market))

    def _handle_sync_steamdt_base(self) -> None:
        if self.steamdt is None:
            self._send_json(
                {"error": "SteamDT API Key is not configured"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            service = SteamDTService(self.steamdt, self.repository)
            count = asyncio.run(service.sync_base_items())
        except Exception as error:
            self._send_json(
                {"error": "SteamDT base sync failed", "detail": str(error)},
                status=HTTPStatus.BAD_GATEWAY,
            )
            return
        self._send_json({"synced": count, "total": self.repository.count()})

    def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def seed_demo_items_if_empty(repository: ItemRepository) -> None:
    if repository.count() > 0:
        return
    repository.upsert_many(
        [
            ItemInput(
                market_hash_name="AK-47 | The Empress (Field-Tested)",
                name_cn="皇后",
                name_en="AK-47 | The Empress",
                category="rifle",
                rarity="Covert",
                aliases=(ItemAliasInput(source="BUFF", source_item_id="demo-buff-1", source_name="BUFF"),),
            ),
            ItemInput(
                market_hash_name="AWP | Asiimov (Battle-Scarred)",
                name_cn="二西莫夫",
                name_en="AWP | Asiimov",
                category="sniper",
                rarity="Covert",
                aliases=(ItemAliasInput(source="BUFF", source_item_id="demo-buff-2", source_name="BUFF"),),
            ),
            ItemInput(
                market_hash_name="M4A1-S | Printstream (Minimal Wear)",
                name_cn="印花集",
                name_en="M4A1-S | Printstream",
                category="rifle",
                rarity="Covert",
                aliases=(ItemAliasInput(source="BUFF", source_item_id="demo-buff-3", source_name="BUFF"),),
            ),
            ItemInput(
                market_hash_name="Desert Eagle | Printstream (Field-Tested)",
                name_cn="印花集",
                name_en="Desert Eagle | Printstream",
                category="pistol",
                rarity="Covert",
                aliases=(ItemAliasInput(source="BUFF", source_item_id="demo-buff-4", source_name="BUFF"),),
            ),
        ]
    )


def build_steamdt_client(context: AppContext) -> SteamDTClient | None:
    api_key = context.settings.steamdt.api_key.strip()
    if not api_key:
        return None
    return SteamDTClient(api_key=api_key, base_url=context.settings.steamdt.base_url)


def build_steamdt_quote(
    item: ItemRecord,
    prices: list[SteamDTPlatformPrice],
    market_settings: Any,
) -> dict[str, Any]:
    positive_prices = [price for price in prices if price.sell_price > 0]
    buy_price = _lowest_price(positive_prices)
    sell_price = _steam_sell_price(positive_prices) or _highest_price(positive_prices)
    profit = None

    if buy_price is not None and sell_price is not None:
        result = ProfitCalculator().calculate(
            buy_price.sell_price,
            sell_price.sell_price,
            steam_fee_rate=Decimal(str(market_settings.steam_fee_rate)),
            wallet_discount_rate=Decimal(str(market_settings.wallet_discount_rate)),
        )
        if result is not None:
            profit = {
                "net_sell_price": _money(result.net_sell_price),
                "profit": _money(result.profit),
                "roi": _percent(result.roi),
                "spread": _percent(result.spread),
            }

    return {
        "item": _item_to_json(item),
        "sources": {
            "buy": _source_json(buy_price, "SteamDT 最低挂单"),
            "sell": _source_json(sell_price, "SteamDT 卖出估算"),
        },
        "profit": profit,
        "platform_prices": [_platform_price_json(price) for price in positive_prices],
        "warning": "当前价格来自 SteamDT 实时接口；利润为按配置手续费计算的估算值。",
        "live": True,
    }


def build_demo_quote(item: ItemRecord, market_settings: Any) -> dict[str, Any]:
    buy_price, sell_price = _demo_prices(item)
    result = ProfitCalculator().calculate(
        buy_price,
        sell_price,
        steam_fee_rate=Decimal(str(market_settings.steam_fee_rate)),
        wallet_discount_rate=Decimal(str(market_settings.wallet_discount_rate)),
    )
    if result is None:
        profit = None
    else:
        profit = {
            "net_sell_price": _money(result.net_sell_price),
            "profit": _money(result.profit),
            "roi": _percent(result.roi),
            "spread": _percent(result.spread),
        }

    return {
        "item": _item_to_json(item),
        "sources": {
            "buy": {
                "name": "BUFF 演示价",
                "price": _money(buy_price),
                "freshness": "本地演示数据",
            },
            "sell": {
                "name": "SteamDT 演示价",
                "price": _money(sell_price),
                "freshness": "本地演示数据",
            },
        },
        "profit": profit,
        "platform_prices": [],
        "warning": "当前为本地演示报价；接入真实 SteamDT/Buff 数据后会替换。",
        "live": False,
    }


def _lowest_price(prices: list[SteamDTPlatformPrice]) -> SteamDTPlatformPrice | None:
    if not prices:
        return None
    return min(prices, key=lambda price: price.sell_price)


def _highest_price(prices: list[SteamDTPlatformPrice]) -> SteamDTPlatformPrice | None:
    if not prices:
        return None
    return max(prices, key=lambda price: price.sell_price)


def _steam_sell_price(prices: list[SteamDTPlatformPrice]) -> SteamDTPlatformPrice | None:
    steam_prices = [price for price in prices if "steam" in price.platform.lower()]
    return _highest_price(steam_prices)


def _source_json(price: SteamDTPlatformPrice | None, fallback_name: str) -> dict[str, str]:
    if price is None:
        return {
            "name": fallback_name,
            "price": "-",
            "freshness": "暂无数据",
        }
    return {
        "name": f"{price.platform} · {fallback_name}",
        "price": _money(price.sell_price),
        "freshness": f"在售 {price.sell_count} 件",
    }


def _platform_price_json(price: SteamDTPlatformPrice) -> dict[str, Any]:
    return {
        "platform": price.platform,
        "platform_item_id": price.platform_item_id,
        "sell_price": _money(price.sell_price),
        "sell_count": price.sell_count,
        "bidding_price": _money(price.bidding_price),
        "bidding_count": price.bidding_count,
        "update_time": price.update_time,
    }


def _demo_prices(item: ItemRecord) -> tuple[Decimal, Decimal]:
    base = Decimal(120 + (sum(ord(char) for char in item.market_hash_name) % 700))
    if item.category == "sniper":
        base *= Decimal("1.45")
    elif item.category == "pistol":
        base *= Decimal("0.72")
    buy_price = base.quantize(Decimal("0.01"))
    sell_price = (buy_price * Decimal("1.36")).quantize(Decimal("0.01"))
    return buy_price, sell_price


def _item_to_json(item: ItemRecord) -> dict[str, Any]:
    return asdict(item)


def _money(value: Decimal) -> str:
    return f"¥{quantize_money(Decimal(str(value)))}"


def _percent(value: Decimal) -> str:
    return f"{quantize_percent(Decimal(str(value)))}%"


def _first(query: dict[str, list[str]], key: str, default: str) -> str:
    values = query.get(key)
    if not values:
        return default
    return values[0]


def _parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except ValueError:
        return default


if __name__ == "__main__":
    main()
