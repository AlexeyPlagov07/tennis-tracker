import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from bs4 import BeautifulSoup


@dataclass
class ProductData:
    url: str
    name: Optional[str]
    brand: Optional[str]
    sku: Optional[str]
    price: Optional[float]
    in_stock: Optional[bool]
    scraped_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class ProductParseError(Exception):
    """Raised when a product page yields no usable price under any parsing strategy."""


class ProductParser:
    """
    Extracts product name/brand/sku/price/stock from a retailer's product page HTML,
    using the source-specific selector config defined in config/sources.yaml.
    """

    # Matches e.g. "329.00" or "329" inside strings like "$329.00" once commas are stripped.
    PRICE_PATTERN = re.compile(r"\d+(?:\.\d+)?")

    def parse(self, html: str, url: str, parser_config: dict) -> ProductData:
        soup = BeautifulSoup(html, "lxml")

        fields = self._parse_container(soup, parser_config)
        if (fields is None or fields.get("price") is None) and parser_config.get("json_ld"):
            fields = self._parse_json_ld(soup)
        if fields is None or fields.get("price") is None:
            fields = self._parse_fallback(soup, parser_config)

        if fields is None or fields.get("price") is None:
            raise ProductParseError(f"Could not extract a price from {url}")

        # Availability is resolved independently of whichever strategy produced the rest of
        # the fields above, except JSON-LD, which already carries its own availability value.
        in_stock = fields.get("in_stock")
        if in_stock is None:
            in_stock = self._parse_availability(soup, parser_config.get("availability_selector"))

        return ProductData(
            url=url,
            name=fields.get("name"),
            brand=fields.get("brand"),
            sku=fields.get("sku"),
            price=fields.get("price"),
            in_stock=in_stock,
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )

    def _parse_container(self, soup: BeautifulSoup, parser_config: dict) -> Optional[dict]:
        container_selector = parser_config.get("container_selector")
        attributes = parser_config.get("attributes")
        if not container_selector or not attributes:
            return None

        element = soup.select_one(container_selector)
        if element is None:
            return None

        fields = {field: element.get(attr) for field, attr in attributes.items()}
        fields["price"] = self._to_price(fields.get("price"))
        return fields

    def _parse_fallback(self, soup: BeautifulSoup, parser_config: dict) -> Optional[dict]:
        fallback = parser_config.get("fallback")
        if not fallback:
            return None

        name_el = soup.select_one(fallback["name_selector"]) if fallback.get("name_selector") else None
        price_el = soup.select_one(fallback["price_selector"]) if fallback.get("price_selector") else None
        if price_el is None:
            return None

        price_text = price_el.get("content") or price_el.get_text()
        return {
            "name": name_el.get_text(strip=True) if name_el else None,
            "brand": None,
            "sku": None,
            "price": self._to_price(price_text),
        }

    def _parse_json_ld(self, soup: BeautifulSoup) -> Optional[dict]:
        # Shopify (and many other storefronts) embed a schema.org Product block per page;
        # `offers` may be a single object or a list of per-variant offers.
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            entries: list = data.get("@graph", [data]) if isinstance(data, dict) else data if isinstance(data, list) else []
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("@type") != "Product":
                    continue

                offers = entry.get("offers")
                if isinstance(offers, list):
                    offers = offers[0] if offers else None
                if not isinstance(offers, dict) or "price" not in offers:
                    continue

                brand = entry.get("brand")
                return {
                    "name": entry.get("name"),
                    "brand": brand.get("name") if isinstance(brand, dict) else brand,
                    "sku": entry.get("sku") or offers.get("sku"),
                    "price": self._to_price(offers.get("price")),
                    "in_stock": self._availability_from_text(offers.get("availability")),
                }
        return None

    def _parse_availability(self, soup: BeautifulSoup, availability_selector: Optional[str]) -> Optional[bool]:
        if not availability_selector:
            return None

        element = soup.select_one(availability_selector)
        if element is None:
            return None

        return self._availability_from_text(element.get("content") or element.get_text())

    def _availability_from_text(self, value: Any) -> Optional[bool]:
        if not value:
            return None
        value = str(value).strip().lower()
        if "instock" in value or "in stock" in value:
            return True
        if "outofstock" in value or "out of stock" in value or "sold out" in value:
            return False
        return None

    def _to_price(self, raw: Any) -> Optional[float]:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        match = self.PRICE_PATTERN.search(str(raw).replace(",", ""))
        return float(match.group(0)) if match else None
