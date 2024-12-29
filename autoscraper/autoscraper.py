"""Main AutoScraper class implementation."""

from typing import Any
from loguru import logger
from dotenv import load_dotenv

from .agents.navigator import NavigatorAgent
from .agents.generator import GeneratorAgent
from .agents.debugger import DebuggerAgent
from .utils.spider_runner import SpiderRunner
from .config import OUTPUT_PATH
from pathlib import Path
import re
from urllib.parse import urlparse


class AutoScraper:
    """Main class for generating and testing scrapers."""

    def __init__(self):
        """Initialize the scraper with agents."""
        load_dotenv()
        logger.add("output/autoscraper.log", rotation="500 MB")
        self.navigator = NavigatorAgent()
        self.generator = GeneratorAgent()
        self.debugger = DebuggerAgent(self.navigator)
        self.spider_runner = SpiderRunner()
        self.target_fields = None
        self.base_url = None
        self.start_url = None

    def analyze_website(self, base_url: str, start_url: str) -> None:
        """Analyze the website structure.

        Args:
            base_url: The base URL of the website
            start_url: The starting URL for navigation
        """
        self.base_url = base_url
        self.start_url = start_url
        logger.info(f"Analyzing website structure for {base_url}")
        self.website_structure = self.navigator.analyse_website(start_url)

    def set_target_fields(self, target_fields: dict[str, str]) -> None:
        """Set the target fields to scrape.

        Args:
            target_fields: Dictionary mapping field names to their types
        """
        self.target_fields = target_fields

    def _get_spider_name(self) -> str:
        """Generate a spider name from the base URL."""
        parsed = urlparse(self.base_url)
        name = re.sub(r"\.[^.]+$", "", parsed.netloc.split(".")[-2])
        name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
        return name

    def generate(self) -> None:
        """Generate and test the scraper."""
        if not self.target_fields or not self.base_url:
            raise ValueError("Website analysis and target fields must be set first")

        spider_name = self._get_spider_name()
        self.output_dir = OUTPUT_PATH / f"{spider_name}_spider"
        debugging_history: list[dict[str, Any]] = []

        # Setup project directory
        self.spider_path = self.generator.file_manager.setup_project(Path("autoscraper/base_project"), self.output_dir, spider_name)

        max_attempts = 20
        attempt = 1
        debug_result = None

        while attempt <= max_attempts:
            logger.info(f"Attempt {attempt} of {max_attempts}")

            # Generate spider code
            self.generator.generate_spider(
                website_structure=self.website_structure,
                target_fields=self.target_fields,
                spider_name=spider_name,
                output_dir=self.output_dir,
                debug_result=debug_result,
            )

            # Test the spider
            debug_result = self.debugger.test_scraper(Path(self.spider_path), self.output_dir, self.website_structure, debugging_history)
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

    def run(self) -> None:
        """Run the generated scraper."""
        if not hasattr(self, "spider_path") or not hasattr(self, "output_dir"):
            raise ValueError("Scraper must be generated before running")

        # Run the spider without timeout
        success, stdout, stderr, items_scraped = self.spider_runner.run_spider(self.spider_path, self.output_dir)

        if not success:
            logger.error("Scraper failed to run successfully")
