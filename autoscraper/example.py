"""Example usage of AutoScraper for Vinted website."""

from .autoscraper import AutoScraper

if __name__ == "__main__":
    # Example usage for Vinted
    scraper = AutoScraper()
    scraper.analyze_website(base_url="https://www.vinted.fr", start_url="https://www.vinted.fr/catalog/10-dresses")
    scraper.set_target_fields(
        {
            "item_name": "str",
            "price": "str",
            "tags": "list[str]",
            "description": "str",
            "image_urls": "list[str]",
            "url": "str",
            "brand": "str",
            "size": "str",
            "color": "str",
            "material": "str",
            "condition": "str",
            "location": "str",
            "seller_name": "str",
            "seller_url": "str",
            "seller_rating": "str",
        }
    )
    scraper.generate()
    scraper.run()
