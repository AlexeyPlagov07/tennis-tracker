import requests


class RequestsCollector:
    """
    Responsible for downloading a webpage using HTTP.
    """

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def collect(self, url: str) -> str:
        """
        Download a webpage and return its HTML.
        """

        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=self.timeout
        )

        response.raise_for_status()

        return response.text