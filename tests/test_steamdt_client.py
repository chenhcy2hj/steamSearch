from __future__ import annotations

import unittest
from decimal import Decimal

from app.core.errors import AuthError, ExternalApiError, RateLimitError
from app.core.rate_limiter import AsyncFixedWindowRateLimiter
from app.steamdt.client import HttpRequest, HttpResponse, SteamDTClient


class FakeTransport:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.requests: list[HttpRequest] = []

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        return self.response


def no_wait_limiter() -> AsyncFixedWindowRateLimiter:
    return AsyncFixedWindowRateLimiter()


class SteamDTClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_base_items(self) -> None:
        transport = FakeTransport(
            HttpResponse(
                200,
                {
                    "success": True,
                    "errorCode": 0,
                    "data": [
                        {
                            "name": "皇后",
                            "marketHashName": "AK-47 | The Empress (Field-Tested)",
                            "platformList": [{"name": "BUFF", "itemId": "123"}],
                        }
                    ],
                },
            )
        )
        client = SteamDTClient("token", transport=transport, rate_limiter=no_wait_limiter())

        items = await client.fetch_base_items()

        self.assertEqual(transport.requests[0].method, "GET")
        self.assertEqual(transport.requests[0].url, "https://open.steamdt.com/open/cs2/v1/base")
        self.assertEqual(transport.requests[0].headers["Authorization"], "Bearer token")
        self.assertEqual(items[0].market_hash_name, "AK-47 | The Empress (Field-Tested)")
        self.assertEqual(items[0].platform_list[0].item_id, "123")

    async def test_fetch_single_price(self) -> None:
        transport = FakeTransport(
            HttpResponse(
                200,
                {
                    "success": True,
                    "errorCode": 0,
                    "data": [
                        {
                            "platform": "buff",
                            "platformItemId": "123",
                            "sellPrice": 159.5,
                            "sellCount": 42,
                            "biddingPrice": 150,
                            "biddingCount": 12,
                            "updateTime": 1710000000,
                        }
                    ],
                },
            )
        )
        client = SteamDTClient("token", transport=transport, rate_limiter=no_wait_limiter())

        prices = await client.fetch_single_price("AK-47 | The Empress (Field-Tested)")

        self.assertEqual(transport.requests[0].query["marketHashName"], "AK-47 | The Empress (Field-Tested)")
        self.assertEqual(prices[0].sell_price, Decimal("159.5"))
        self.assertEqual(prices[0].sell_count, 42)
        self.assertEqual(prices[0].bidding_price, Decimal("150"))

    async def test_fetch_batch_prices(self) -> None:
        transport = FakeTransport(
            HttpResponse(
                200,
                {
                    "success": True,
                    "errorCode": 0,
                    "data": [
                        {
                            "marketHashName": "AK-47 | The Empress (Field-Tested)",
                            "dataList": [
                                {
                                    "platform": "steam",
                                    "platformItemId": "456",
                                    "sellPrice": 220,
                                    "sellCount": 8,
                                    "biddingPrice": 210,
                                    "biddingCount": 4,
                                    "updateTime": 1710000001,
                                }
                            ],
                        }
                    ],
                },
            )
        )
        client = SteamDTClient("token", transport=transport, rate_limiter=no_wait_limiter())

        prices = await client.fetch_batch_prices(["AK-47 | The Empress (Field-Tested)"])

        self.assertEqual(transport.requests[0].method, "POST")
        self.assertEqual(transport.requests[0].json_body["marketHashNames"][0], "AK-47 | The Empress (Field-Tested)")
        self.assertEqual(prices[0].data_list[0].platform, "steam")

    async def test_fetch_kline(self) -> None:
        transport = FakeTransport(
            HttpResponse(
                200,
                {
                    "success": True,
                    "errorCode": 0,
                    "data": [[{"time": 1710000000, "price": 200}]],
                },
            )
        )
        client = SteamDTClient("token", transport=transport, rate_limiter=no_wait_limiter())

        points = await client.fetch_kline("AK-47 | The Empress (Field-Tested)", platform="steam")

        self.assertEqual(transport.requests[0].url, "https://open.steamdt.com/open/cs2/item/v1/kline")
        self.assertEqual(transport.requests[0].json_body["type"], 1)
        self.assertEqual(transport.requests[0].json_body["platform"], "steam")
        self.assertEqual(points[0].raw["price"], 200)

    async def test_raises_for_auth_and_rate_limit_http_status(self) -> None:
        auth_client = SteamDTClient(
            "token",
            transport=FakeTransport(HttpResponse(401, {})),
            rate_limiter=no_wait_limiter(),
        )
        rate_client = SteamDTClient(
            "token",
            transport=FakeTransport(HttpResponse(429, {})),
            rate_limiter=no_wait_limiter(),
        )

        with self.assertRaises(AuthError):
            await auth_client.fetch_base_items()
        with self.assertRaises(RateLimitError):
            await rate_client.fetch_base_items()

    async def test_raises_for_steamdt_error_payload(self) -> None:
        client = SteamDTClient(
            "token",
            transport=FakeTransport(
                HttpResponse(
                    200,
                    {
                        "success": False,
                        "errorCode": 4001,
                        "errorMsg": "请输入正确的 app-Key",
                    },
                )
            ),
            rate_limiter=no_wait_limiter(),
        )

        with self.assertRaises(ExternalApiError):
            await client.fetch_base_items()


if __name__ == "__main__":
    unittest.main()

