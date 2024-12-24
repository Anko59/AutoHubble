"""Scrapy settings for the base spider template."""

import sys

from loguru import logger

# Configure loguru
logger.remove()  # Remove default handler
logger.add(sys.stdout, level="INFO")
logger.add("spider.log", rotation="500 MB", level="DEBUG")

BOT_NAME = "base_spider"

SPIDER_MODULES = ["base_spider.spiders"]
NEWSPIDER_MODULE = "base_spider.spiders"

# Crawl responsibly by identifying yourself
USER_AGENT = "AutoScraper (+https://github.com/yourusername/autoscraper)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 16

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 1

# Enable and configure Zyte API
ZYTE_API_KEY = "YOUR_ZYTE_API_KEY"
ADDONS = {
    "scrapy_zyte_api.Addon": 500,
}

# Configure logging
LOG_LEVEL = "INFO"

# Configure output paths
FEEDS = {
    "output/%(name)s/%(name)s_%(batch_time)s.json": {
        "format": "json",
        "encoding": "utf8",
        "store_empty": False,
        "overwrite": True,
        "item_export_kwargs": {
            "export_empty_fields": True,
        },
    },
}

FEED_EXPORT_BATCH_ITEM_COUNT = 100
