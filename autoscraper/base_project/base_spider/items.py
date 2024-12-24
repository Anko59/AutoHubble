"""Base item definition for scraped data."""

from scrapy import Item, Field


class ScrapedItem(Item):
    """Base item class for scraped data.

    Fields will be added by the generator agent based on target fields.
    """

    # Fields will be added by the generator agent
    pass
