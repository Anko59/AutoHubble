"""Base spider template for generated scrapers."""

from collections.abc import Generator

from loguru import logger
from scrapy import Request, Spider
from scrapy.http import Response


class BaseSpider(Spider):
    """Base spider class for generated scrapers."""

    name = "base_spider"
    start_urls: list[str] = []

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests.

        Yields:
            Requests for the start URLs
        """
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse, meta={"zyte_api_automap": True})

    def parse(self, response: Response) -> Generator[dict, None, None]:
        """Parse the response and extract data.

        This method should be overridden by generated spiders.

        Args:
            response: The response to parse

        Yields:
            Extracted items
        """
        logger.warning("This is a base spider - implement parsing logic")
        yield {}
