from __future__ import annotations

import unittest
from decimal import Decimal

from app.buff.client import BuffClient, BuffHttpRequest, BuffHttpResponse
from app.core.errors import AuthError, RateLimitError


class FakeBuffTransport:
    def __init__(self, responses: list[BuffHttpResponse]) -> None:
        self.responses = responses
        self.requests: list[BuffHttpRequest] = []

    async def __call__(self, request: BuffHttpRequest) -> BuffHttpResponse:
        self.requests.append(request)
        return self.responses.pop(0)


class BuffClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_listing_summary_searches_goods_then_sell_orders(self) -> None:
        transport = FakeBuffTransport(
            [
                BuffHttpResponse(
                    200,
                    {
                        "code": "OK",
                        "data": {
                            "items": [
                                {
                                    "id": 123,
                                    "market_hash_name": "AK-47 | The Empress (Field-Tested)",
                                    "name": "皇后",
                                }
                            ]
                        },
                    },
                ),
                BuffHttpResponse(
                    200,
                    {
                        "code": "OK",
                        "data": {
                            "total_count": 42,
                            "items": [{"price": "159.00"}],
                        },
                    },
                ),
            ]
        )
        client = BuffClient(cookie="cookie", transport=transport)

        summary = await client.fetch_listing_summary("AK-47 | The Empress (Field-Tested)")

        self.assertEqual(transport.requests[0].url, "https://buff.163.com/api/market/goods")
        self.assertEqual(transport.requests[1].url, "https://buff.163.com/api/market/goods/sell_order")
        self.assertEqual(transport.requests[1].query["goods_id"], "123")
        self.assertEqual(summary.lowest_price, Decimal("159.00"))
        self.assertEqual(summary.sell_count, 42)

    async def test_fetch_listing_summary_can_use_known_goods_id(self) -> None:
        transport = FakeBuffTransport(
            [
                BuffHttpResponse(
                    200,
                    {
                        "code": "OK",
                        "data": {
                            "total_count": 7,
                            "items": [{"price": "88.80"}],
                        },
                    },
                )
            ]
        )
        client = BuffClient(cookie="cookie", transport=transport)

        summary = await client.fetch_listing_summary("Example Item", goods_id="known-id")

        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(transport.requests[0].query["goods_id"], "known-id")
        self.assertEqual(summary.lowest_price, Decimal("88.80"))

    async def test_raises_for_auth_and_rate_limit(self) -> None:
        auth_client = BuffClient(
            cookie="cookie",
            transport=FakeBuffTransport([BuffHttpResponse(401, {})]),
        )
        rate_client = BuffClient(
            cookie="cookie",
            transport=FakeBuffTransport([BuffHttpResponse(429, {})]),
        )

        with self.assertRaises(AuthError):
            await auth_client.fetch_listing_summary("Item", goods_id="1")
        with self.assertRaises(RateLimitError):
            await rate_client.fetch_listing_summary("Item", goods_id="1")


if __name__ == "__main__":
    unittest.main()

