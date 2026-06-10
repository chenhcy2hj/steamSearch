from __future__ import annotations

import argparse
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

    server = build_server(args.host, args.port, context, item_repository)
    print(f"SteamSearch Browser running at http://{args.host}:{args.port}")
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
) -> HTTPServer:
    class SteamSearchHandler(BrowserRequestHandler):
        app_context = context
        repository = item_repository

    return HTTPServer((host, port), SteamSearchHandler)


class BrowserRequestHandler(BaseHTTPRequestHandler):
    app_context: AppContext
    repository: ItemRepository

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
        self._send_json(build_demo_quote(item, self.app_context.settings.market))

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
        "warning": "当前为本地演示报价；接入真实 SteamDT/Buff 数据后会替换。",
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
    return f"¥{quantize_money(value)}"


def _percent(value: Decimal) -> str:
    return f"{quantize_percent(value)}%"


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
