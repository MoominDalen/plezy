"""Unit tests for John Lewis parsing (no live network)."""

import unittest

from jl_client import (
    StockSnapshot,
    _extract_skus,
    _extract_title,
    _is_available,
    _snapshots_from_page_html,
)


class TestAvailability(unittest.TestCase):
    def test_in_stock_status(self) -> None:
        self.assertTrue(_is_available("SKU_AVAILABLE", 3))

    def test_out_of_stock_status(self) -> None:
        self.assertFalse(_is_available("OUT_OF_STOCK", 0))

    def test_quantity_fallback(self) -> None:
        self.assertTrue(_is_available("UNKNOWN", 1))


class TestSkuExtraction(unittest.TestCase):
    def test_extracts_sku_from_json(self) -> None:
        html = '{"skuId":"240280782","productName":"Pokemon TCG Tin"}'
        self.assertIn("240280782", _extract_skus(html))

    def test_extracts_title(self) -> None:
        html = "<title>Pokemon Cards | John Lewis</title>"
        self.assertEqual(_extract_title(html), "Pokemon Cards")


class TestPageFallback(unittest.TestCase):
    def test_detects_add_to_basket(self) -> None:
        html = "<button>Add to basket</button>" + ("x" * 100)
        snaps = _snapshots_from_page_html(
            html,
            ["240280782"],
            product_name="Test",
            product_url="https://www.johnlewis.com/test/p1",
        )
        self.assertEqual(len(snaps), 1)
        self.assertTrue(snaps[0].available)


if __name__ == "__main__":
    unittest.main()
