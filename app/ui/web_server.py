from __future__ import annotations

import argparse
import asyncio
import json
import socket
from dataclasses import asdict
from decimal import Decimal
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from app.bootstrap import AppContext, bootstrap_app
from app.buff.client import BuffClient
from app.buff.dto import BuffListingSummary
from app.buff.service import BuffService
from app.market.calculator import ProfitCalculator, quantize_money, quantize_percent
from app.storage.models import ItemAliasInput, ItemInput, ItemRecord, WatchlistInput, WatchlistRecord
from app.storage.repositories.items import ItemRepository
from app.storage.repositories.watchlist import WatchlistRepository
from app.steamdt.client import SteamDTClient
from app.steamdt.dto import SteamDTPlatformPrice
from app.steamdt.service import SteamDTService
from app.ui.pages.browser import render_browser_page


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PORT_FALLBACK_ATTEMPTS = 20


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, no_demo_data: bool = False) -> None:
    context = bootstrap_app()
    item_repository = ItemRepository(context.database)
    watchlist_repository = WatchlistRepository(context.database)
    if not no_demo_data:
        seed_demo_items_if_empty(item_repository)

    steamdt_client = build_steamdt_client(context)
    buff_service = build_buff_service(context)
    selected_port = find_available_port(host, port)
    if selected_port != port:
        print(f"Port {port} is already in use. Using {selected_port} instead.")
    server = build_server(
        host,
        selected_port,
        context,
        item_repository,
        watchlist_repository,
        steamdt_client,
        buff_service,
    )
    print(f"SteamSearch Browser running at http://{host}:{selected_port}")
    if steamdt_client is None:
        print("SteamDT live API disabled. Set STEAMDT_API_KEY or config/config.local.toml.")
    else:
        print("SteamDT live API enabled.")
    if buff_service is None:
        print("BUFF enhancement disabled. Set BUFF_ENABLED=true and BUFF_COOKIE to enable it.")
    else:
        print("BUFF enhancement enabled.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SteamSearch Browser.")
    finally:
        context.database.close()
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SteamSearch lightweight browser UI.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    parser.add_argument("--no-demo-data", action="store_true")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, no_demo_data=args.no_demo_data)


def build_server(
    host: str,
    port: int,
    context: AppContext,
    item_repository: ItemRepository,
    watchlist_repository: WatchlistRepository,
    steamdt_client: SteamDTClient | None = None,
    buff_service: BuffService | None = None,
) -> HTTPServer:
    class SteamSearchHandler(BrowserRequestHandler):
        app_context = context
        repository = item_repository
        watchlist = watchlist_repository
        steamdt = steamdt_client
        buff = buff_service

    return HTTPServer((host, port), SteamSearchHandler)


def find_available_port(
    host: str,
    start_port: int,
    max_attempts: int = PORT_FALLBACK_ATTEMPTS,
    port_checker: Callable[[str, int], bool] | None = None,
) -> int:
    checker = port_checker or is_port_available
    for port in range(start_port, start_port + max_attempts):
        if checker(host, port):
            return port
    raise OSError(f"No available port found from {start_port} to {start_port + max_attempts - 1}")


def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


class BrowserRequestHandler(BaseHTTPRequestHandler):
    app_context: AppContext
    repository: ItemRepository
    watchlist: WatchlistRepository
    steamdt: SteamDTClient | None
    buff: BuffService | None

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
                    },
                    "buff": {
                        "enabled": self.buff is not None,
                    },
                }
            )
            return
        if parsed.path == "/api/watchlist":
            self._handle_list_watchlist()
            return
        if parsed.path == "/health":
            self._send_json({"ok": True})
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/watchlist":
            self._handle_add_watchlist()
            return
        if parsed.path.startswith("/api/watchlist/") and parsed.path.endswith("/toggle"):
            watchlist_id = _parse_path_id(parsed.path, prefix="/api/watchlist/", suffix="/toggle")
            self._handle_toggle_watchlist(watchlist_id)
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/watchlist/"):
            watchlist_id = _parse_path_id(parsed.path, prefix="/api/watchlist/", suffix="")
            self._handle_delete_watchlist(watchlist_id)
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
            self._send_json(build_demo_quote(item, self.app_context.settings.market, self._fetch_buff(item)))
            return

        try:
            prices = asyncio.run(self.steamdt.fetch_single_price(item.market_hash_name))
        except Exception as error:
            self._send_json(
                {
                    "error": "SteamDT request failed",
                    "detail": str(error),
                    "fallback": build_demo_quote(item, self.app_context.settings.market, self._fetch_buff(item)),
                },
                status=HTTPStatus.BAD_GATEWAY,
            )
            return

        self._send_json(build_steamdt_quote(item, prices, self.app_context.settings.market, self._fetch_buff(item)))

    def _handle_list_watchlist(self) -> None:
        self._send_json({"items": [_watchlist_to_json(item) for item in self.watchlist.list_all()]})

    def _handle_add_watchlist(self) -> None:
        payload = self._read_json_body()
        market_hash_name = str(payload.get("market_hash_name") or "")
        item = self.repository.get_by_market_hash_name(market_hash_name)
        if item is None:
            self._send_json({"error": "item not found"}, status=HTTPStatus.NOT_FOUND)
            return

        watchlist_id = self.watchlist.add(
            WatchlistInput(
                item_id=item.id,
                target_buy_price=_optional_float(payload.get("target_buy_price")),
                target_roi=_optional_float(payload.get("target_roi")),
                note=_optional_string(payload.get("note")),
            )
        )
        self._send_json({"id": watchlist_id}, status=HTTPStatus.CREATED)

    def _handle_toggle_watchlist(self, watchlist_id: int | None) -> None:
        if watchlist_id is None:
            self._send_json({"error": "invalid watchlist id"}, status=HTTPStatus.BAD_REQUEST)
            return
        payload = self._read_json_body()
        enabled = bool(payload.get("enabled", True))
        if not self.watchlist.set_enabled(watchlist_id, enabled):
            self._send_json({"error": "watchlist item not found"}, status=HTTPStatus.NOT_FOUND)
            return
        self._send_json({"id": watchlist_id, "enabled": enabled})

    def _handle_delete_watchlist(self, watchlist_id: int | None) -> None:
        if watchlist_id is None:
            self._send_json({"error": "invalid watchlist id"}, status=HTTPStatus.BAD_REQUEST)
            return
        if not self.watchlist.delete(watchlist_id):
            self._send_json({"error": "watchlist item not found"}, status=HTTPStatus.NOT_FOUND)
            return
        self._send_json({"id": watchlist_id, "deleted": True})

    def _fetch_buff(self, item: ItemRecord) -> BuffListingSummary | Exception | None:
        if self.buff is None:
            return None
        try:
            return asyncio.run(self.buff.fetch_listing_summary(item.market_hash_name))
        except Exception as error:
            return error

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

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length") or "0")
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload


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


def build_buff_service(context: AppContext) -> BuffService | None:
    if not context.settings.buff.enabled:
        return None
    cookie = context.settings.buff.cookie.strip()
    if not cookie:
        return None
    return BuffService(
        BuffClient(cookie=cookie),
        min_interval_seconds=context.settings.buff.min_interval_seconds,
        cache_ttl_seconds=context.settings.buff.cache_ttl_seconds,
    )


def build_steamdt_quote(
    item: ItemRecord,
    prices: list[SteamDTPlatformPrice],
    market_settings: Any,
    buff_summary: BuffListingSummary | Exception | None = None,
) -> dict[str, Any]:
    positive_prices = [price for price in prices if price.sell_price > 0]
    steamdt_buy_price = _lowest_price(positive_prices)
    sell_price = _steam_sell_price(positive_prices) or _highest_price(positive_prices)
    buy_price = _quote_buy_price(steamdt_buy_price, buff_summary)
    profit = None

    if buy_price is not None and sell_price is not None:
        result = ProfitCalculator().calculate(
            buy_price["amount"],
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
            "buy": _buy_source_json(buy_price),
            "sell": _source_json(sell_price, "SteamDT 卖出估算"),
        },
        "profit": profit,
        "platform_prices": [_platform_price_json(price) for price in positive_prices],
        "warning": _quote_warning("SteamDT", buff_summary),
        "live": True,
    }


def build_demo_quote(
    item: ItemRecord,
    market_settings: Any,
    buff_summary: BuffListingSummary | Exception | None = None,
) -> dict[str, Any]:
    demo_buy_price, sell_price = _demo_prices(item)
    buy_price = _quote_buy_price(None, buff_summary)
    raw_buy_price = buy_price["amount"] if buy_price is not None else demo_buy_price
    result = ProfitCalculator().calculate(
        raw_buy_price,
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
            "buy": _buy_source_json(
                buy_price
                or {
                    "name": "BUFF 演示价",
                    "amount": demo_buy_price,
                    "freshness": "本地演示数据",
                }
            ),
            "sell": {
                "name": "SteamDT 演示价",
                "price": _money(sell_price),
                "freshness": "本地演示数据",
            },
        },
        "profit": profit,
        "platform_prices": [],
        "warning": _quote_warning("演示数据", buff_summary),
        "live": False,
    }


def _quote_buy_price(
    steamdt_price: SteamDTPlatformPrice | None,
    buff_summary: BuffListingSummary | Exception | None,
) -> dict[str, Any] | None:
    if isinstance(buff_summary, BuffListingSummary):
        return {
            "name": "BUFF 实时最低挂单",
            "amount": buff_summary.lowest_price,
            "freshness": _buff_freshness(buff_summary),
        }
    if steamdt_price is None:
        return None
    return {
        "name": f"{steamdt_price.platform} · SteamDT 最低挂单",
        "amount": steamdt_price.sell_price,
        "freshness": f"在售 {steamdt_price.sell_count} 件",
    }


def _buy_source_json(price: dict[str, Any] | None) -> dict[str, str]:
    if price is None:
        return {
            "name": "买入价",
            "price": "-",
            "freshness": "暂无数据",
        }
    return {
        "name": str(price["name"]),
        "price": _money(price["amount"]),
        "freshness": str(price["freshness"]),
    }


def _buff_freshness(summary: BuffListingSummary) -> str:
    if summary.sell_count is None:
        return "BUFF 当前挂单"
    return f"BUFF 在售 {summary.sell_count} 件"


def _quote_warning(source_name: str, buff_summary: BuffListingSummary | Exception | None) -> str:
    if isinstance(buff_summary, Exception):
        return f"{source_name} 已返回；BUFF 增强失败：{buff_summary}"
    if isinstance(buff_summary, BuffListingSummary):
        return f"{source_name} 已返回；买入价使用 BUFF 实时最低挂单。"
    return f"当前价格来自 {source_name}；未启用 BUFF 增强。"


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


def _watchlist_to_json(item: WatchlistRecord) -> dict[str, Any]:
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


def _parse_path_id(path: str, prefix: str, suffix: str) -> int | None:
    if not path.startswith(prefix):
        return None
    value = path[len(prefix) :]
    if suffix:
        if not value.endswith(suffix):
            return None
        value = value[: -len(suffix)]
    try:
        return int(value)
    except ValueError:
        return None


def _optional_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


if __name__ == "__main__":
    main()
