from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import SupportsFloat

from app.market.models import ProfitInput, ProfitResult

NumericValue = str | int | float | Decimal | SupportsFloat


class ProfitCalculator:
    def calculate(
        self,
        buy_price: NumericValue,
        sell_price: NumericValue,
        steam_fee_rate: NumericValue = Decimal("0.15"),
        wallet_discount_rate: NumericValue = Decimal("1.0"),
    ) -> ProfitResult | None:
        data = ProfitInput(
            buy_price=to_decimal(buy_price),
            sell_price=to_decimal(sell_price),
            steam_fee_rate=to_decimal(steam_fee_rate),
            wallet_discount_rate=to_decimal(wallet_discount_rate),
        )
        return calculate_profit(data)


def calculate_profit(data: ProfitInput) -> ProfitResult | None:
    _validate_rates(data.steam_fee_rate, data.wallet_discount_rate)

    if data.buy_price <= 0 or data.sell_price <= 0:
        return None

    net_sell_price = data.sell_price * (Decimal("1") - data.steam_fee_rate)
    net_sell_price *= data.wallet_discount_rate

    profit = net_sell_price - data.buy_price
    roi = profit / data.buy_price
    spread = data.sell_price / data.buy_price - Decimal("1")

    return ProfitResult(
        buy_price=data.buy_price,
        sell_price=data.sell_price,
        net_sell_price=net_sell_price,
        profit=profit,
        roi=roi,
        spread=spread,
    )


def to_decimal(value: NumericValue) -> Decimal:
    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"Invalid numeric value: {value!r}") from error


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def quantize_percent(value: Decimal) -> Decimal:
    return (value * Decimal("100")).quantize(Decimal("0.01"))


def _validate_rates(steam_fee_rate: Decimal, wallet_discount_rate: Decimal) -> None:
    if steam_fee_rate < 0 or steam_fee_rate >= 1:
        raise ValueError("steam_fee_rate must be greater than or equal to 0 and less than 1")
    if wallet_discount_rate <= 0:
        raise ValueError("wallet_discount_rate must be greater than 0")

