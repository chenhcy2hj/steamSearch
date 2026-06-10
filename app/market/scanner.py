from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.market.calculator import ProfitCalculator


@dataclass(frozen=True)
class RadarCandidate:
    item_id: int
    market_hash_name: str
    name_cn: str | None
    category: str | None
    buy_price: Decimal
    sell_price: Decimal


@dataclass(frozen=True)
class RadarFilters:
    min_profit: Decimal = Decimal("0")
    min_roi: Decimal = Decimal("0")
    limit: int = 20


@dataclass(frozen=True)
class RadarResult:
    item_id: int
    market_hash_name: str
    name_cn: str | None
    category: str | None
    buy_price: Decimal
    sell_price: Decimal
    net_sell_price: Decimal
    profit: Decimal
    roi: Decimal
    spread: Decimal
    risk_score: Decimal


class RadarScanner:
    def __init__(
        self,
        steam_fee_rate: Decimal = Decimal("0.15"),
        wallet_discount_rate: Decimal = Decimal("1.0"),
    ) -> None:
        self.steam_fee_rate = steam_fee_rate
        self.wallet_discount_rate = wallet_discount_rate
        self.calculator = ProfitCalculator()

    def scan(
        self,
        candidates: Iterable[RadarCandidate],
        filters: RadarFilters | None = None,
    ) -> list[RadarResult]:
        filters = filters or RadarFilters()
        results: list[RadarResult] = []

        for candidate in candidates:
            profit = self.calculator.calculate(
                candidate.buy_price,
                candidate.sell_price,
                steam_fee_rate=self.steam_fee_rate,
                wallet_discount_rate=self.wallet_discount_rate,
            )
            if profit is None:
                continue
            if profit.profit < filters.min_profit or profit.roi < filters.min_roi:
                continue
            results.append(
                RadarResult(
                    item_id=candidate.item_id,
                    market_hash_name=candidate.market_hash_name,
                    name_cn=candidate.name_cn,
                    category=candidate.category,
                    buy_price=profit.buy_price,
                    sell_price=profit.sell_price,
                    net_sell_price=profit.net_sell_price,
                    profit=profit.profit,
                    roi=profit.roi,
                    spread=profit.spread,
                    risk_score=_risk_score(profit.roi),
                )
            )

        results.sort(key=lambda result: (result.roi, result.profit), reverse=True)
        return results[: max(filters.limit, 0)]


def build_demo_radar_candidate(
    item_id: int,
    market_hash_name: str,
    name_cn: str | None,
    category: str | None,
) -> RadarCandidate:
    base = Decimal(120 + (sum(ord(char) for char in market_hash_name) % 700))
    if category == "sniper":
        base *= Decimal("1.45")
    elif category == "pistol":
        base *= Decimal("0.72")

    buy_price = base.quantize(Decimal("0.01"))
    sell_price = (buy_price * Decimal("1.36")).quantize(Decimal("0.01"))
    return RadarCandidate(
        item_id=item_id,
        market_hash_name=market_hash_name,
        name_cn=name_cn,
        category=category,
        buy_price=buy_price,
        sell_price=sell_price,
    )


def _risk_score(roi: Decimal) -> Decimal:
    score = Decimal("70") + min(max(roi * Decimal("100"), Decimal("0")), Decimal("25"))
    return score.quantize(Decimal("0.01"))
