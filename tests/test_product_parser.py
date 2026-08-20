import pytest

from src.parsers.product_parser import ProductParseError, ProductParser

PARSER_CONFIG = {
    "container_selector": "div.desc_top.gtm_detail",
    "attributes": {
        "name": "data-gtm_detail_name",
        "price": "data-gtm_detail_price",
        "brand": "data-gtm_detail_brand",
        "sku": "data-gtm_detail_stock_number",
    },
    "fallback": {
        "name_selector": "h1",
        "price_selector": "[itemprop='price']",
    },
    "availability_selector": "[itemprop='availability']",
}

CONTAINER_HTML = """
<html><body>
<div class="desc_top gtm_detail"
     data-gtm_detail_name="Wilson RF 01 Racquet"
     data-gtm_detail_price="329.00"
     data-gtm_detail_brand="Wilson"
     data-gtm_detail_stock_number="WR151411U">
</div>
<link itemprop="availability" content="http://schema.org/InStock" />
</body></html>
"""


def test_parses_container_strategy():
    product = ProductParser().parse(CONTAINER_HTML, "https://example.com/racket", PARSER_CONFIG)

    assert product.name == "Wilson RF 01 Racquet"
    assert product.price == 329.00
    assert product.brand == "Wilson"
    assert product.sku == "WR151411U"
    assert product.in_stock is True


def test_falls_back_to_microdata_when_container_missing():
    html = """
    <html><body>
      <h1>Some Racket</h1>
      <span itemprop="price" content="99.99">$99.99</span>
      <link itemprop="availability" content="http://schema.org/OutOfStock" />
    </body></html>
    """
    product = ProductParser().parse(html, "https://example.com/other", PARSER_CONFIG)

    assert product.name == "Some Racket"
    assert product.price == 99.99
    assert product.in_stock is False


def test_raises_when_no_price_found():
    html = "<html><body><p>Nothing here</p></body></html>"
    with pytest.raises(ProductParseError):
        ProductParser().parse(html, "https://example.com/empty", PARSER_CONFIG)


def test_parses_json_ld_with_single_offer():
    html = """
    <html><body><script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Product",
      "name": "Pro Staff 97 Classic Tennis Racquet",
      "brand": {"@type": "Brand", "name": "Wilson"},
      "sku": "705274",
      "offers": {
        "@type": "Offer",
        "price": "299.00",
        "availability": "https://schema.org/InStock"
      }
    }
    </script></body></html>
    """
    product = ProductParser().parse(html, "https://example.com/json-ld", {"json_ld": True})

    assert product.name == "Pro Staff 97 Classic Tennis Racquet"
    assert product.brand == "Wilson"
    assert product.sku == "705274"
    assert product.price == 299.00
    assert product.in_stock is True


def test_parses_json_ld_with_offer_list_and_numeric_price():
    html = """
    <html><body><script type="application/ld+json">
    {
      "@type": "Product",
      "name": "Wilson Pro Staff 97 Classic",
      "brand": {"@type": "Brand", "name": "Wilson"},
      "sku": "103319",
      "offers": [
        {"@type": "Offer", "price": 299.00, "availability": "http://schema.org/InStock"},
        {"@type": "Offer", "price": 299.00, "availability": "http://schema.org/InStock"}
      ]
    }
    </script></body></html>
    """
    product = ProductParser().parse(html, "https://example.com/json-ld-list", {"json_ld": True})

    assert product.price == 299.00
    assert product.in_stock is True
