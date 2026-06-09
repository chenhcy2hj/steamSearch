from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProfitInput:
    buy_price: Decimal
    sell_price: Decimal
    steam_fee_rate: Decimal = Decimal("0.15")
    wallet_discount_rate: Decimal = Decimal("1.0")


@dataclass(frozen=True)
class ProfitResult:
    buy_price: Decimal
    sell_price: Decimal
    net_sell_price: Decimal
    profit: Decimal
    roi: Decimal
    spread: Decimal

