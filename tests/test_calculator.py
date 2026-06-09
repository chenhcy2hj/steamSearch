from __future__ import annotations

import unittest
from decimal import Decimal

from app.market.calculator import (
    ProfitCalculator,
    calculate_profit,
    quantize_money,
    quantize_percent,
)
from app.market.models import ProfitInput


class ProfitCalculatorTest(unittest.TestCase):
    def test_calculates_profit_after_steam_fee(self) -> None:
        result = calculate_profit(
            ProfitInput(
                buy_price=Decimal("100"),
                sell_price=Decimal("200"),
                steam_fee_rate=Decimal("0.15"),
            )
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.net_sell_price, Decimal("170.00"))
        self.assertEqual(result.profit, Decimal("70.00"))
        self.assertEqual(result.roi, Decimal("0.70"))
        self.assertEqual(result.spread, Decimal("1"))

    def test_applies_wallet_discount(self) -> None:
        result = calculate_profit(
            ProfitInput(
                buy_price=Decimal("100"),
                sell_price=Decimal("200"),
                steam_fee_rate=Decimal("0.15"),
                wallet_discount_rate=Decimal("0.90"),
            )
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.net_sell_price, Decimal("153.0000"))
        self.assertEqual(result.profit, Decimal("53.0000"))

    def test_returns_none_when_price_is_not_positive(self) -> None:
        self.assertIsNone(
            calculate_profit(
                ProfitInput(
                    buy_price=Decimal("0"),
                    sell_price=Decimal("200"),
                )
            )
        )
        self.assertIsNone(
            calculate_profit(
                ProfitInput(
                    buy_price=Decimal("100"),
                    sell_price=Decimal("0"),
                )
            )
        )

    def test_rejects_invalid_rates(self) -> None:
        with self.assertRaises(ValueError):
            calculate_profit(
                ProfitInput(
                    buy_price=Decimal("100"),
                    sell_price=Decimal("200"),
                    steam_fee_rate=Decimal("1"),
                )
            )

        with self.assertRaises(ValueError):
            calculate_profit(
                ProfitInput(
                    buy_price=Decimal("100"),
                    sell_price=Decimal("200"),
                    wallet_discount_rate=Decimal("0"),
                )
            )

    def test_calculator_converts_common_numeric_inputs(self) -> None:
        result = ProfitCalculator().calculate("159.00", 251.54)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.buy_price, Decimal("159.00"))
        self.assertEqual(result.sell_price, Decimal("251.54"))

    def test_quantizers_prepare_values_for_display(self) -> None:
        self.assertEqual(quantize_money(Decimal("54.809")), Decimal("54.81"))
        self.assertEqual(quantize_percent(Decimal("0.14234")), Decimal("14.23"))


if __name__ == "__main__":
    unittest.main()

