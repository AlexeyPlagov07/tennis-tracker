from src.database.database import Database
from src.parsers.product_parser import ProductData


def make_product(scraped_at: str, price: float = 329.00, in_stock: bool = True) -> ProductData:
    return ProductData(
        url="https://example.com/racket",
        name="Wilson RF 01",
        brand="Wilson",
        sku="WR1",
        price=price,
        in_stock=in_stock,
        scraped_at=scraped_at,
    )


def test_save_and_read_back(tmp_path):
    db = Database(tmp_path / "test.db")
    product_id = db.save_product_snapshot("tennis_warehouse", make_product("2026-08-20T00:00:00+00:00"))

    latest = db.get_latest_prices()
    assert len(latest) == 1
    assert latest[0]["price"] == 329.00

    history = db.get_price_history(product_id)
    assert len(history) == 1


def test_price_history_accumulates_and_latest_wins(tmp_path):
    db = Database(tmp_path / "test.db")
    db.save_product_snapshot("tennis_warehouse", make_product("2026-08-19T00:00:00+00:00", price=329.00))
    db.save_product_snapshot("tennis_warehouse", make_product("2026-08-20T00:00:00+00:00", price=299.00))

    latest = db.get_latest_prices()
    assert len(latest) == 1
    assert latest[0]["price"] == 299.00

    history = db.get_price_history(latest[0]["id"])
    assert len(history) == 2
