from __future__ import annotations

import unittest
from decimal import Decimal

from app.market.scanner import RadarCandidate, RadarFilters, RadarScanner


class RadarScannerTest(unittest.TestCase):
    def test_scan_filters_and_sorts_by_roi(self) -> None:
        scanner = RadarScanner(steam_fee_rate=Decimal("0.15"))
        candidates = [
            RadarCandidate(
                item_id=1,
                market_hash_name="Low ROI",
                name_cn=None,
                category=None,
                buy_price=Decimal("100"),
                sell_price=Decimal("110"),
            ),
            RadarCandidate(
                item_id=2,
                market_hash_name="High ROI",
                name_cn=None,
                category=None,
                buy_price=Decimal("100"),
                sell_price=Decimal("150"),
            ),
        ]

        results = scanner.scan(
            candidates,
            RadarFilters(min_profit=Decimal("1"), min_roi=Decimal("0.10"), limit=10),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].market_hash_name, "High ROI")
        self.assertEqual(results[0].profit, Decimal("27.50"))


if __name__ == "__main__":
    unittest.main()
