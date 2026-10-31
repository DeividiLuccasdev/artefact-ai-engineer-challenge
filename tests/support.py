"""Synthetic fixtures: no original customer data."""
import csv
from pathlib import Path


def write_fixture(directory: Path):
    tables = {
        "categories": (["category_id", "name", "description"], [[1, "Violões", "Acoustic guitars"]]),
        "products": (["product_id", "name", "category_id", "description", "price_brl",
                      "stock_quantity", "status", "specs"], [
            [1, "Demo Guitar", 1, "Nylon study instrument", "999.90", 2, "active", "{}"],
            [2, "Future Guitar", 1, "Future instrument", "500", 5, "coming_soon", "{}"],
            [3, "Empty Guitar", 1, "Steel instrument", "300", 0, "active", "{}"]]),
        "promotions": (["promotion_id", "product_id", "discount_percent", "description", "is_active"],
                       [[1, 1, 10, "Demo", 1], [2, 1, 20, "Expired", 0]]),
        "orders": (["order_id", "customer_id", "status", "tracking_code", "estimated_delivery"],
                   [[1, 10, "shipped", "DEMO-TRACKING", "2026-11-04"],
                    [2, 20, "pending", "", ""]]),
        "order_items": (["order_id", "product_id", "quantity"], [[1, 1, 1], [2, 1, 1]])}
    for name, (columns, rows) in tables.items():
        with (directory / f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(columns)
            writer.writerows(rows)
