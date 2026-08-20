"""
Entry point for a full scrape run: reads config/sources.yaml, collects each
configured product page, parses it, and stores the result in the database.
Per-product failures are logged and skipped so one bad page can't halt the run.
"""
import logging

import yaml

from src.collectors.playwright_collector import PlaywrightCollector
from src.collectors.requests_collector import RequestsCollector
from src.database.database import Database
from src.parsers.product_parser import ProductParseError, ProductParser
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def load_sources(config_path: str = "config/sources.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run() -> None:
    setup_logging()
    sources = load_sources().get("sources", {})
    db = Database()
    parser = ProductParser()
    requests_collector = RequestsCollector()

    # One browser instance is reused for every playwright-based product in this run.
    with PlaywrightCollector() as playwright_collector:
        for source_id, source_cfg in sources.items():
            collector = (
                playwright_collector if source_cfg.get("collector") == "playwright" else requests_collector
            )
            parser_config = source_cfg.get("parser", {})

            for product_cfg in source_cfg.get("products", []):
                url = product_cfg["url"]
                try:
                    html = collector.collect(url)
                    product = parser.parse(html, url, parser_config)
                    db.save_product_snapshot(source_id, product)
                    logger.info("Saved %s: $%s (in_stock=%s)", product.name, product.price, product.in_stock)
                except ProductParseError as exc:
                    logger.error("Parse failed for %s: %s", url, exc)
                except Exception:
                    logger.exception("Unexpected error scraping %s", url)


if __name__ == "__main__":
    run()
