from __future__ import annotations

import asyncio
import unittest

from app.core.rate_limiter import AsyncFixedWindowRateLimiter


class AsyncFixedWindowRateLimiterTest(unittest.IsolatedAsyncioTestCase):
    async def test_allows_unconfigured_key(self) -> None:
        limiter = AsyncFixedWindowRateLimiter()

        await limiter.acquire("unknown")

    async def test_delays_when_limit_is_reached(self) -> None:
        limiter = AsyncFixedWindowRateLimiter()
        limiter.configure("demo", 1, 0.01)

        await limiter.acquire("demo")
        started = asyncio.get_running_loop().time()
        await limiter.acquire("demo")
        elapsed = asyncio.get_running_loop().time() - started

        self.assertGreaterEqual(elapsed, 0.008)


if __name__ == "__main__":
    unittest.main()

