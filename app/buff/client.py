from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Awaitable, Callable, Mapping
from urllib import parse, request
from urllib.error import HTTPError, URLError

from app.buff.dto import BuffGoods, BuffListingSummary
from app.core.errors import AuthError, DataParseError, ExternalApiError, RateLimitError

Transport = Callable[["BuffHttpRequest"], Awaitable["BuffHttpResponse"]]


@dataclass(frozen=True)
class BuffHttpRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    query: Mapping[str, str] | None = None
    timeout: float = 15.0


@dataclass(frozen=True)
class BuffHttpResponse:
    status_code: int
    json_data: Mapping[str, Any]


class BuffClient:
    def __init__(
        self,
        cookie: str,
        base_url: str = "https://buff.163.com",
        transport: Transport | None = None,
    ) -> None:
        self.cookie = cookie
        self.base_url = base_url.rstrip("/")
        self._transport = transport or default_transport

    async def fetch_listing_summary(
        self,
        market_hash_name: str,
        goods_id: str | None = None,
    ) -> BuffListingSummary:
        goods = BuffGoods(goods_id=goods_id, market_hash_name=market_hash_name, name=market_hash_name)
        if not goods.goods_id:
            goods = await self.search_goods(market_hash_name)
        return await self.fetch_sell_order_summary(goods)

    async def search_goods(self, market_hash_name: str) -> BuffGoods:
        data = await self._request(
            "/api/market/goods",
            {
                "game": "csgo",
                "page_num": "1",
                "page_size": "10",
                "search": market_hash_name,
            },
        )
        items = _ensure_list(_nested(data, "items"))
        if not items:
            raise DataParseError(f"BUFF goods not found: {market_hash_name}")

        selected = _select_goods(items, market_hash_name)
        return BuffGoods(
            goods_id=str(selected.get("id") or selected.get("goods_id") or ""),
            market_hash_name=str(selected.get("market_hash_name") or market_hash_name),
            name=str(selected.get("name") or market_hash_name),
        )

    async def fetch_sell_order_summary(self, goods: BuffGoods) -> BuffListingSummary:
        data = await self._request(
            "/api/market/goods/sell_order",
            {
                "game": "csgo",
                "goods_id": goods.goods_id,
                "page_num": "1",
                "sort_by": "default",
                "mode": "",
                "allow_tradable_cooldown": "1",
            },
        )
        items = _ensure_list(_nested(data, "items"))
        if not items:
            raise DataParseError(f"BUFF sell order not found: {goods.market_hash_name}")

        first = _ensure_mapping(items[0])
        price = _decimal(first.get("price"))
        total_count = _int_or_none(_nested(data, "total_count"))
        return BuffListingSummary(
            goods_id=goods.goods_id,
            market_hash_name=goods.market_hash_name,
            lowest_price=price,
            sell_count=total_count,
        )

    async def _request(self, path: str, query: Mapping[str, str]) -> Any:
        response = await self._transport(
            BuffHttpRequest(
                method="GET",
                url=f"{self.base_url}{path}",
                headers=self._headers(),
                query=query,
            )
        )
        _raise_for_status(response.status_code)
        return _unwrap_response(response.json_data)

    def _headers(self) -> Mapping[str, str]:
        return {
            "Accept": "application/json",
            "Cookie": self.cookie,
            "Referer": f"{self.base_url}/market/csgo",
            "User-Agent": "Mozilla/5.0 SteamSearch/0.1",
        }


async def default_transport(http_request: BuffHttpRequest) -> BuffHttpResponse:
    return await asyncio.to_thread(_send_request, http_request)


def _send_request(http_request: BuffHttpRequest) -> BuffHttpResponse:
    url = _build_url(http_request.url, http_request.query)
    req = request.Request(url=url, headers=dict(http_request.headers), method=http_request.method)
    try:
        with request.urlopen(req, timeout=http_request.timeout) as response:
            payload = response.read().decode("utf-8")
            return BuffHttpResponse(response.status, json.loads(payload))
    except HTTPError as error:
        payload = error.read().decode("utf-8") if error.fp is not None else "{}"
        return BuffHttpResponse(error.code, _loads_json_or_empty(payload))
    except URLError as error:
        raise ExternalApiError(f"BUFF request failed: {error.reason}") from error
    except json.JSONDecodeError as error:
        raise DataParseError("BUFF returned invalid JSON") from error


def _build_url(url: str, query: Mapping[str, str] | None) -> str:
    if not query:
        return url
    return f"{url}?{parse.urlencode(query)}"


def _loads_json_or_empty(payload: str) -> Mapping[str, Any]:
    if not payload:
        return {}
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, Mapping):
        return {}
    return data


def _raise_for_status(status_code: int) -> None:
    if status_code in {401, 403}:
        raise AuthError("BUFF authentication failed")
    if status_code == 429:
        raise RateLimitError("BUFF rate limit reached")
    if status_code >= 400:
        raise ExternalApiError(f"BUFF request failed with HTTP {status_code}")


def _unwrap_response(payload: Mapping[str, Any]) -> Any:
    code = payload.get("code")
    if code not in {"OK", "ok", 0, "0", None}:
        message = payload.get("msg") or payload.get("message") or "BUFF API error"
        raise ExternalApiError(str(message))
    return payload.get("data", payload)


def _select_goods(items: list[Any], market_hash_name: str) -> Mapping[str, Any]:
    for item in items:
        row = _ensure_mapping(item)
        if row.get("market_hash_name") == market_hash_name:
            return row
    return _ensure_mapping(items[0])


def _nested(data: Any, key: str) -> Any:
    if not isinstance(data, Mapping):
        return None
    return data.get(key)


def _ensure_list(data: Any) -> list[Any]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    raise DataParseError("Expected BUFF data to be a list")


def _ensure_mapping(data: Any) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise DataParseError("Expected BUFF item to be an object")
    return data


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise DataParseError(f"Invalid decimal value: {value!r}") from error


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

