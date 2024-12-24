"""Main script for generating and testing scrapers."""

import re
from pathlib import Path
from urllib.parse import urlparse
from loguru import logger
from dotenv import load_dotenv

from .agents.navigator import NavigatorAgent
from .agents.generator import GeneratorAgent
from .agents.debugger import DebuggerAgent
from .config import OUTPUT_PATH


def get_spider_name(url: str) -> str:
    """Generate a spider name from a URL.

    Args:
        url: Website URL to generate name from

    Returns:
        Spider name suitable for file/directory naming
    """
    parsed = urlparse(url)
    # Get domain without TLD and clean it
    name = re.sub(r"\.[^.]+$", "", parsed.netloc.split(".")[-2])
    # Remove non-alphanumeric chars and convert to snake case
    name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
    return name


def main(base_url: str, start_url: str, target_fields: dict[str, str]) -> None:
    """Generate and test a spider for the given website.

    Args:
        url: Website URL to scrape
        target_fields: Dictionary mapping field names to their types
    """
    # Load environment variables
    load_dotenv()

    # Set up logging
    logger.add("autoscraper.log", rotation="500 MB")
    logger.info(f"Starting scraper generation for {base_url}")

    # Generate spider name and setup output dir
    spider_name = get_spider_name(base_url)
    output_dir = OUTPUT_PATH / f"{spider_name}_spider"
    debugging_history = []

    try:
        # Initialize agents
        navigator = NavigatorAgent(base_url=base_url)
        generator = GeneratorAgent()
        debugger = DebuggerAgent()

        # Step 1: Analyze the website
        logger.info("Analyzing website structure")
        website_structure = navigator.analyse_website(start_url)

        # Step 2: Generate and test spider with feedback loop
        max_attempts = 20
        attempt = 1
        debug_result = None

        spider_path = generator.file_manager.setup_project(Path("autoscraper/base_project"), output_dir, spider_name)
        while attempt <= max_attempts:
            logger.info(f"Attempt {attempt} of {max_attempts}")

            # Generate spider code with debug feedback if available
            logger.info("Generating spider code")
            generator.generate_spider(
                website_structure=website_structure,
                target_fields=target_fields,
                spider_name=spider_name,
                debug_result=debug_result,
                output_dir=output_dir,
            )

            # Test the spider
            logger.info("Testing spider")
            debug_result = debugger.test_scraper(Path(spider_path), output_dir, website_structure, debugging_history)
            debugging_history.append(debug_result.model_dump())

            if debug_result.success:
                logger.info(f"Spider test successful! Scraped {debug_result.items_scraped} items")
                break
            else:
                logger.warning("Spider test failed")
                logger.info("Recommendations for improvement:")
                logger.info(debug_result.recommendations)

                attempt += 1
                if attempt > max_attempts:
                    logger.error("Max attempts reached, spider generation failed")
                    break

    except Exception as e:
        logger.exception(f"Error during scraper generation: {str(e)}")
        raise


if __name__ == "__main__":
    # Example usage
    start_url = "https://www.vinted.fr/catalog/10-dresses"
    base_url = "https://www.vinted.fr"
    target_fields = {
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
    main(base_url, start_url, target_fields)
