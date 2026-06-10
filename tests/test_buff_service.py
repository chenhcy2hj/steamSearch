from __future__ import annotations

import unittest
from decimal import Decimal

from app.buff.dto import BuffListingSummary
from app.buff.service import BuffService


class FakeBuffClient:
    def __init__(self) -> None:
        self.calls = 0

    async def fetch_listing_summary(
        self,
        market_hash_name: str,
        goods_id: str | None = None,
    ) -> BuffListingSummary:
        self.calls += 1
        return BuffListingSummary(
            goods_id=goods_id or "generated",
            market_hash_name=market_hash_name,
            lowest_price=Decimal("123.45"),
            sell_count=5,
        )


class BuffServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_uses_cache_within_ttl(self) -> None:
        client = FakeBuffClient()
        service = BuffService(client, min_interval_seconds=0, cache_ttl_seconds=60)

        first = await service.fetch_listing_summary("AK-47 | The Empress (Field-Tested)")
        second = await service.fetch_listing_summary("AK-47 | The Empress (Field-Tested)")

        self.assertEqual(first, second)
        self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()
