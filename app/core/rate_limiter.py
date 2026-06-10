from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: float


class AsyncFixedWindowRateLimiter:
    def __init__(self) -> None:
        self._rules: Dict[str, RateLimitRule] = {}
        self._events: Dict[str, Deque[float]] = {}
        self._lock = asyncio.Lock()

    def configure(self, key: str, limit: int, window_seconds: float) -> None:
        if limit <= 0:
            raise ValueError("limit must be greater than 0")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than 0")
        self._rules[key] = RateLimitRule(limit=limit, window_seconds=window_seconds)
        self._events.setdefault(key, deque())

    async def acquire(self, key: str) -> None:
        rule = self._rules.get(key)
        if rule is None:
            return

        while True:
            async with self._lock:
                now = time.monotonic()
                events = self._events.setdefault(key, deque())
                _drop_expired(events, now, rule.window_seconds)

                if len(events) < rule.limit:
                    events.append(now)
                    return

                sleep_for = rule.window_seconds - (now - events[0])

            await asyncio.sleep(max(sleep_for, 0.001))


def build_steamdt_rate_limiter() -> AsyncFixedWindowRateLimiter:
    limiter = AsyncFixedWindowRateLimiter()
    limiter.configure("steamdt.base", 1, 24 * 60 * 60)
    limiter.configure("steamdt.price.single", 60, 60)
    limiter.configure("steamdt.price.batch", 1, 60)
    limiter.configure("steamdt.kline", 120, 60)
    return limiter


def _drop_expired(events: Deque[float], now: float, window_seconds: float) -> None:
    while events and now - events[0] >= window_seconds:
        events.popleft()

