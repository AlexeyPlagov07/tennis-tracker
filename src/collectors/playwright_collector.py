from typing import Optional

from playwright.sync_api import sync_playwright


class PlaywrightCollector:
    """
    Downloads a fully-rendered webpage using a headless browser, for sites whose
    product data is populated client-side by JavaScript instead of plain HTML.

    Can be used as a context manager to reuse a single browser instance across
    many collect() calls (much faster than relaunching a browser per page):

        with PlaywrightCollector() as collector:
            for url in urls:
                html = collector.collect(url)
    """

    def __init__(self, timeout_ms: int = 30_000, headless: bool = True):
        self.timeout_ms = timeout_ms
        self.headless = headless
        self._playwright = None
        self._browser = None

    def __enter__(self) -> "PlaywrightCollector":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._browser = None
        self._playwright = None

    def collect(self, url: str) -> str:
        if self._browser is not None:
            return self._render(self._browser, url)

        # Not used as a context manager: spin up a throwaway browser for this one call.
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.headless)
            try:
                return self._render(browser, url)
            finally:
                browser.close()

    def _render(self, browser, url: str) -> str:
        page = browser.new_page(user_agent="Mozilla/5.0")
        try:
            page.goto(url, timeout=self.timeout_ms, wait_until="networkidle")
            return page.content()
        finally:
            page.close()
