import unittest
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from emporio.data import StoreData, money
from support import write_fixture


class DataTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        write_fixture(Path(self.temp.name))
        self.store = StoreData(Path(self.temp.name))

    def test_discount_not_stacked_and_budget_uses_actual_price(self):
        result = self.store.search_products(category="violoes", payment="pix", max_price_brl="900")
        self.assertEqual(result["total_matches"], 1)
        quote = result["products"][0]
        self.assertEqual(quote["price_brl"], "899.91")
        self.assertEqual(quote["discount_percent"], "10")
        self.assertFalse(quote["stock_reserved"])

    def test_future_and_empty_products_are_not_available(self):
        self.assertEqual(self.store.search_products()["total_matches"], 1)
        self.assertEqual(self.store.search_products(available_only=False)["total_matches"], 3)

    def test_category_words_in_free_text_do_not_hide_valid_products(self):
        result = self.store.search_products(query="violões", category="Violões", max_price_brl="1000")
        self.assertEqual(result["total_matches"], 1)
        self.assertEqual(result["products"][0]["name"], "Demo Guitar")

    def test_order_cannot_be_enumerated_or_read_by_another_customer(self):
        denied = self.store.get_order(1, 20)
        self.assertEqual(denied, self.store.get_order(999, 20))
        self.assertEqual(denied, self.store.get_order(1, None))
        self.assertEqual(self.store.get_order(1, 10)["status"], "shipped")
        self.assertNotIn("customer_id", self.store.get_order(1, 10))

    def test_parallel_reads_cannot_mutate_snapshot(self):
        def read(_):
            result = self.store.search_products()
            result["products"][0]["stock_quantity"] = 999
            return self.store.search_products()["products"][0]["stock_quantity"]
        with ThreadPoolExecutor(max_workers=12) as executor:
            self.assertEqual(list(executor.map(read, range(100))), [2] * 100)

    def test_decimal_and_invalid_inputs(self):
        self.assertEqual(money("1.005"), Decimal("1.01"))
        for value in ("NaN", "Infinity", "-1", "oops"):
            with self.assertRaises(ValueError):
                money(value)
        with self.assertRaises(ValueError):
            self.store.search_products(limit=True)

    def test_duplicate_primary_key_fails_startup(self):
        path = Path(self.temp.name) / "categories.csv"
        with path.open("a", encoding="utf-8") as stream:
            stream.write("1,Duplicate,Duplicate\n")
        with self.assertRaises(ValueError):
            StoreData(Path(self.temp.name))
