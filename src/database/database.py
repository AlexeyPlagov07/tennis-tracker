import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Union

from src.parsers.product_parser import ProductData

_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    name TEXT,
    brand TEXT,
    sku TEXT,
    first_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price REAL,
    in_stock INTEGER,
    scraped_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id);
"""


class Database:
    """SQLite-backed store for tracked products and their price history over time."""

    def __init__(self, db_path: Union[str, Path] = "data/processed/tennis_tracker.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def upsert_product(self, source: str, product: ProductData) -> int:
        # Parameterized throughout: values never get string-formatted into the SQL.
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO products (source, url, name, brand, sku, first_seen)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    name = excluded.name,
                    brand = excluded.brand,
                    sku = excluded.sku
                """,
                (source, product.url, product.name, product.brand, product.sku, product.scraped_at),
            )
            conn.commit()
            row = conn.execute("SELECT id FROM products WHERE url = ?", (product.url,)).fetchone()
            return row[0]

    def insert_price(self, product_id: int, product: ProductData) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO price_history (product_id, price, in_stock, scraped_at) VALUES (?, ?, ?, ?)",
                (
                    product_id,
                    product.price,
                    None if product.in_stock is None else int(product.in_stock),
                    product.scraped_at,
                ),
            )
            conn.commit()

    def save_product_snapshot(self, source: str, product: ProductData) -> int:
        """Upsert the product record and record a new price-history row in one call."""
        product_id = self.upsert_product(source, product)
        self.insert_price(product_id, product)
        return product_id

    def get_latest_prices(self) -> list:
        query = """
            SELECT p.id, p.source, p.name, p.brand, p.url, ph.price, ph.in_stock, ph.scraped_at
            FROM products p
            JOIN price_history ph ON ph.product_id = p.id
            WHERE ph.scraped_at = (SELECT MAX(scraped_at) FROM price_history WHERE product_id = p.id)
            ORDER BY p.name
        """
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]

    def get_price_history(self, product_id: int) -> list:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT price, in_stock, scraped_at FROM price_history WHERE product_id = ? ORDER BY scraped_at",
                (product_id,),
            ).fetchall()
            return [dict(row) for row in rows]
