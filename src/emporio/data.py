"""Validated immutable CSV snapshots. Monetary arithmetic never uses floats."""

import csv
import hashlib
import json
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from types import MappingProxyType


def normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c))


def money(value) -> Decimal:
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise ValueError("Amount must be finite and non-negative")
        return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    category: str
    description: str
    price: Decimal
    stock: int
    status: str
    discount: Decimal

    def quote(self, payment: str) -> dict:
        # Promotions win over PIX: they are never stacked.
        discount = self.discount or (Decimal(5) if payment == "pix" else Decimal(0))
        price = money(self.price * (1 - discount / 100))
        return {"product_id": self.id, "name": self.name, "category": self.category,
                "description": self.description, "stock_quantity": self.stock,
                "status": self.status, "available": self.stock > 0 and self.status == "active",
                "original_price_brl": str(self.price), "price_brl": str(price),
                "discount_percent": str(discount), "promotion_active": self.discount > 0,
                "payment": payment, "stock_reserved": False}


class StoreData:
    """Construct once before serving requests; use a new instance for a new snapshot.

    No runtime reload or mutations: one response cannot mix inventory generations.
    The local source directory must remain unchanged during startup.
    """

    def __init__(self, directory: Path):
        tables = {}
        digest = hashlib.sha256()
        for name in ("categories", "products", "promotions", "orders", "order_items"):
            matches = list(directory.glob(f"*{name}.csv"))
            # 'order_items' does not end in 'orders', but keep matching explicit.
            if len(matches) != 1:
                raise ValueError(f"Expected one {name}.csv file")
            raw = matches[0].read_bytes()
            digest.update(name.encode() + raw)
            tables[name] = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
        self.snapshot_id = digest.hexdigest()[:16]

        def indexed(rows, key):
            result = {}
            for row in rows:
                identifier = int(row[key])
                if identifier <= 0 or identifier in result:
                    raise ValueError(f"Invalid or duplicate {key}")
                result[identifier] = row
            return result

        categories = indexed(tables["categories"], "category_id")
        products = indexed(tables["products"], "product_id")
        promotions = indexed(tables["promotions"], "promotion_id")
        discounts = {}
        for row in promotions.values():
            pid = int(row["product_id"])
            discount = Decimal(row["discount_percent"])
            if pid not in products or not discount.is_finite() or not 0 <= discount <= 100:
                raise ValueError("Invalid promotion reference or percentage")
            if row["is_active"] not in ("0", "1"):
                raise ValueError("Invalid promotion active flag")
            if row["is_active"] == "1":
                # If duplicate active offers exist, choose the greatest, never add them.
                discounts[pid] = max(discounts.get(pid, Decimal(0)), discount)
        parsed = {}
        for pid, row in products.items():
            category = categories[int(row["category_id"])]["name"]
            stock = int(row["stock_quantity"])
            if stock < 0 or row["status"] not in ("active", "discontinued", "inactive", "coming_soon"):
                raise ValueError("Invalid stock or status")
            json.loads(row["specs"])
            parsed[pid] = Product(pid, row["name"], category, row["description"],
                                  money(row["price_brl"]), stock, row["status"],
                                  discounts.get(pid, Decimal(0)))
        self.products = MappingProxyType(parsed)
        orders = indexed(tables["orders"], "order_id")
        for row in tables["order_items"]:
            if (int(row["order_id"]) not in orders or int(row["product_id"]) not in products
                    or int(row["quantity"]) <= 0):
                raise ValueError("Invalid order item")
        self.orders = MappingProxyType({key: MappingProxyType(dict(row))
                                        for key, row in orders.items()})

    def search_products(self, query="", category="", max_price_brl=None,
                        available_only=True, payment="standard", limit=5):
        if payment not in ("standard", "pix"):
            raise ValueError("payment must be standard or pix")
        if type(available_only) is not bool or type(limit) is not int or not 1 <= limit <= 10:
            raise ValueError("Invalid availability or limit")
        if not isinstance(query, str) or not isinstance(category, str):
            raise ValueError("query and category must be strings")
        cap = money(max_price_brl) if max_price_brl is not None else None
        terms = normalize(query).split()
        found = []
        for product in self.products.values():
            haystack = normalize(product.name + " " + product.description + " " + product.category)
            if not all(term in haystack for term in terms):
                continue
            if normalize(category) not in normalize(product.category):
                continue
            quote = product.quote(payment)
            if available_only and not quote["available"]:
                continue
            if cap is None or Decimal(quote["price_brl"]) <= cap:
                found.append(quote)
        found.sort(key=lambda item: (Decimal(item["price_brl"]), item["product_id"]))
        return {"snapshot_id": self.snapshot_id, "total_matches": len(found),
                "products": found[:limit], "notice": "Snapshot availability is not a reservation."}

    def get_order(self, order_id, customer_id):
        # The identity comes from the application, never from model arguments.
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("order_id must be a positive integer")
        row = self.orders.get(order_id)
        if customer_id is None or row is None or int(row["customer_id"]) != customer_id:
            return {"error": "Order unavailable for this session. Contact the store team."}
        # No customer names, emails, notes, payment data, or contact list reach the LLM.
        return {"snapshot_id": self.snapshot_id, "order_id": order_id,
                **{key: row[key] for key in ("status", "tracking_code", "estimated_delivery")},
                "notice": "Provided CSV snapshot, not live carrier tracking. Estimated delivery is not receipt date."}
