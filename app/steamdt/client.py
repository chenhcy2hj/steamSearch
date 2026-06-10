from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Awaitable, Callable, Mapping
from urllib import parse, request
from urllib.error import HTTPError, URLError

from app.core.errors import AuthError, DataParseError, ExternalApiError, RateLimitError
from app.core.rate_limiter import AsyncFixedWindowRateLimiter, build_steamdt_rate_limiter
from app.steamdt.dto import (
    SteamDTBaseItem,
    SteamDTBatchPrice,
    SteamDTKlinePoint,
    SteamDTPlatformInfo,
    SteamDTPlatformPrice,
)

Transport = Callable[["HttpRequest"], Awaitable["HttpResponse"]]


@dataclass(frozen=True)
class HttpRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    query: Mapping[str, str] | None = None
    json_body: Mapping[str, Any] | None = None
    timeout: float = 15.0


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    json_data: Mapping[str, Any]


class SteamDTClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://open.steamdt.com",
        transport: Transport | None = None,
        rate_limiter: AsyncFixedWindowRateLimiter | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._transport = transport or default_transport
        self._rate_limiter = rate_limiter or build_steamdt_rate_limiter()

    async def fetch_base_items(self) -> list[SteamDTBaseItem]:
        await self._rate_limiter.acquire("steamdt.base")
        data = await self._request("GET", "/open/cs2/v1/base")
        return [_parse_base_item(item) for item in _ensure_list(data)]

    async def fetch_single_price(self, market_hash_name: str) -> list[SteamDTPlatformPrice]:
        await self._rate_limiter.acquire("steamdt.price.single")
        data = await self._request(
            "GET",
            "/open/cs2/v1/price/single",
            query={"marketHashName": market_hash_name},
        )
        return [_parse_platform_price(item) for item in _ensure_list(data)]

    async def fetch_batch_prices(self, market_hash_names: list[str]) -> list[SteamDTBatchPrice]:
        await self._rate_limiter.acquire("steamdt.price.batch")
        data = await self._request(
            "POST",
            "/open/cs2/v1/price/batch",
            json_body={"marketHashNames": market_hash_names},
        )
        return [_parse_batch_price(item) for item in _ensure_list(data)]

    async def fetch_kline(
        self,
        market_hash_name: str,
        kline_type: int = 1,
        platform: str = "",
        special_style: str = "",
    ) -> list[SteamDTKlinePoint]:
        await self._rate_limiter.acquire("steamdt.kline")
        data = await self._request(
            "POST",
            "/open/cs2/item/v1/kline",
            json_body={
                "marketHashName": market_hash_name,
                "type": kline_type,
                "platform": platform,
                "specialStyle": special_style,
            },
        )
        return [_parse_kline_point(item) for item in _flatten_kline_data(data)]

    async def _request(
        self,
        method: str,
        path: str,
        query: Mapping[str, str] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> Any:
        response = await self._transport(
            HttpRequest(
                method=method,
                url=f"{self.base_url}{path}",
                headers=self._headers(),
                query=query,
                json_body=json_body,
            )
        )
        _raise_for_status(response.status_code)
        return _unwrap_response(response.json_data)

    def _headers(self) -> Mapping[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }


async def default_transport(http_request: HttpRequest) -> HttpResponse:
    return await asyncio.to_thread(_send_request, http_request)


def _send_request(http_request: HttpRequest) -> HttpResponse:
    url = _build_url(http_request.url, http_request.query)
    body = None
    if http_request.json_body is not None:
        body = json.dumps(http_request.json_body).encode("utf-8")

    req = request.Request(
        url=url,
        data=body,
        headers=dict(http_request.headers),
        method=http_request.method,
    )

    try:
        with request.urlopen(req, timeout=http_request.timeout) as response:
            payload = response.read().decode("utf-8")
            return HttpResponse(response.status, json.loads(payload))
    except HTTPError as error:
        payload = error.read().decode("utf-8") if error.fp is not None else "{}"
        return HttpResponse(error.code, _loads_json_or_empty(payload))
    except URLError as error:
        raise ExternalApiError(f"SteamDT request failed: {error.reason}") from error
    except json.JSONDecodeError as error:
        raise DataParseError("SteamDT returned invalid JSON") from error


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
        raise AuthError("SteamDT authentication failed")
    if status_code == 429:
        raise RateLimitError("SteamDT rate limit reached")
    if status_code >= 400:
        raise ExternalApiError(f"SteamDT request failed with HTTP {status_code}")


def _unwrap_response(payload: Mapping[str, Any]) -> Any:
    if not payload.get("success", False):
        error_code = payload.get("errorCode")
        error_message = payload.get("errorMsg") or "SteamDT API error"
        raise ExternalApiError(f"{error_message} ({error_code})")
    return payload.get("data")


def _ensure_list(data: Any) -> list[Any]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    raise DataParseError("Expected SteamDT data to be a list")


def _parse_base_item(data: Any) -> SteamDTBaseItem:
    item = _ensure_mapping(data)
    platforms = tuple(_parse_platform_info(row) for row in _ensure_list(item.get("platformList", [])))
    return SteamDTBaseItem(
        name=str(item.get("name") or ""),
        market_hash_name=str(item.get("marketHashName") or ""),
        platform_list=platforms,
    )


def _parse_platform_info(data: Any) -> SteamDTPlatformInfo:
    item = _ensure_mapping(data)
    return SteamDTPlatformInfo(
        name=str(item.get("name") or ""),
        item_id=str(item.get("itemId") or ""),
    )


def _parse_platform_price(data: Any) -> SteamDTPlatformPrice:
    item = _ensure_mapping(data)
    return SteamDTPlatformPrice(
        platform=str(item.get("platform") or ""),
        platform_item_id=str(item.get("platformItemId") or ""),
        sell_price=_decimal(item.get("sellPrice")),
        sell_count=_int(item.get("sellCount")),
        bidding_price=_decimal(item.get("biddingPrice")),
        bidding_count=_int(item.get("biddingCount")),
        update_time=_int(item.get("updateTime")),
    )


def _parse_batch_price(data: Any) -> SteamDTBatchPrice:
    item = _ensure_mapping(data)
    prices = tuple(_parse_platform_price(row) for row in _ensure_list(item.get("dataList", [])))
    return SteamDTBatchPrice(
        market_hash_name=str(item.get("marketHashName") or ""),
        data_list=prices,
    )


def _parse_kline_point(data: Any) -> SteamDTKlinePoint:
    if isinstance(data, Mapping):
        return SteamDTKlinePoint(raw=data)
    return SteamDTKlinePoint(raw={"value": data})


def _flatten_kline_data(data: Any) -> list[Any]:
    rows = _ensure_list(data)
    if len(rows) == 1 and isinstance(rows[0], list):
        return rows[0]
    return rows


def _ensure_mapping(data: Any) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise DataParseError("Expected SteamDT item to be an object")
    return data


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise DataParseError(f"Invalid decimal value: {value!r}") from error


def _int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise DataParseError(f"Invalid integer value: {value!r}") from error

