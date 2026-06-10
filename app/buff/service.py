from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from app.buff.client import BuffClient
from app.buff.dto import BuffListingSummary


@dataclass(frozen=True)
class CachedBuffSummary:
    summary: BuffListingSummary
    expires_at: float


class BuffService:
    def __init__(
        self,
        client: BuffClient,
        min_interval_seconds: float = 6,
        cache_ttl_seconds: float = 600,
    ) -> None:
        self.client = client
        self.min_interval_seconds = max(min_interval_seconds, 0)
        self.cache_ttl_seconds = max(cache_ttl_seconds, 0)
        self._cache: dict[str, CachedBuffSummary] = {}
        self._last_request_at = 0.0

    async def fetch_listing_summary(
        self,
        market_hash_name: str,
        goods_id: str | None = None,
    ) -> BuffListingSummary:
        now = time.monotonic()
        cached = self._cache.get(market_hash_name)
        if cached and cached.expires_at > now:
            return cached.summary

        await self._wait_for_interval()
        summary = await self.client.fetch_listing_summary(market_hash_name, goods_id=goods_id)
        self._last_request_at = time.monotonic()
        self._cache[market_hash_name] = CachedBuffSummary(
            summary=summary,
            expires_at=self._last_request_at + self.cache_ttl_seconds,
        )
        return summary

    async def _wait_for_interval(self) -> None:
        if self._last_request_at <= 0 or self.min_interval_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        wait_for = self.min_interval_seconds - elapsed
        if wait_for > 0:
            await asyncio.sleep(wait_for)
