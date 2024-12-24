"""Navigator agent for website analysis using Selenium and LLM."""
import time
from urllib.parse import urljoin

from loguru import logger

from ..config import MAX_DEPTH, MAX_LINKS
from ..models import PageAnalysis, WebsiteAnalysis
from ..utils.chrome_driver import ChromeDriver
from ..utils.html_parser import HTMLParser
from ..utils.openrouter import OpenRouterClient


class NavigatorAgent:
    """Agent responsible for analyzing websites and gathering structural information."""

    def __init__(self, base_url: str) -> None:
        """Initialize the navigator agent."""
        logger.info("Initializing NavigatorAgent")

        self.openrouter = OpenRouterClient()
        self.driver = ChromeDriver()
        self.html_parser = HTMLParser()
        self.base_url = base_url

    def _analyze_page(self, url: str, driver, all_page_analyses: list[PageAnalysis]) -> PageAnalysis:
        """Analyze a webpage to identify its structure and data elements.

        Args:
            url: The URL to analyze

        Returns:
            WebsiteStructure containing the analysis results
        """
        url = url.strip()
        if url.startswith("/"):
            url = urljoin(self.base_url, url)
        logger.info(f"Starting analysis of {url}")

        logger.debug(f"Loading page {url}")
        driver.get(url)
        # Wait for the page to load
        time.sleep(3)
        # Collect page information
        page_source = driver.page_source
        page_source, json_data = self.html_parser.parse(page_source)
        network_requests = self.driver.capture_network_requests(driver)

        # Use LLM to analyze the page
        logger.info("Analyzing page with LLM")
        page_analysis = self._analyze_with_llm(page_source, json_data, network_requests, all_page_analyses)
        if not page_analysis:
            logger.error("Failed to analyze page structure")
            raise ValueError("Page analysis failed")

        page_analysis.url = url
        page_analysis.title = driver.title

        logger.debug("Page analysis:")
        logger.debug(page_analysis.model_dump_json(indent=2))

        return page_analysis

    def _analyze_with_llm(
        self, page_source: str, json_data: list[dict[str, str]], network_requests: list[dict], all_page_analyses: list[PageAnalysis]
    ) -> PageAnalysis | None:
        """Use LLM to analyze the page content and structure.

        Args:
            page_source: HTML source of the page
            network_requests: Captured network requests

        Returns:
            WebsiteAnalysis containing the analysis results, or None if analysis fails
        """
        logger.info("Analyzing page with LLM")
        # Get model configuration

        # Prepare context for the LLM
        context = {
            "task": "Analyze website structure for scraping",
            "information_extracted_from_previous_requests": [page.model_dump() for page in all_page_analyses],
            "page_source": page_source,
            "network_requests": network_requests,
            "json_data": json_data,
            "instructions": [
                "Determine the best method for data extraction (HTML selectors, JSON parsing, API calls)",
                "Identify main content areas and their selectors",
                "Find specific data elements using appropriate patterns (CSS selectors, JSON paths, API endpoints)",
                "Provide sample values for each data element",
                "Identify pagination methods and provide details",
                "Analyze API endpoints in network requests and their structure",
                "Determine if JavaScript is required and if content is dynamic",
                "Identify links to follow for further analysis if needed",
                "Provide any additional remarks or challenges observed",
            ],
        }

        # Log the context for debugging
        logger.debug("Analysis context:")
        logger.debug(f"Page source length: {len(page_source)}")
        logger.debug(f"Found {len(network_requests)} network requests")

        page_analysis = self.openrouter.get_completion(
            model_role="navigator",
            system_prompt="""You are an expert at analyzing websites for scraping with Scrapy.
Analyze the provided website structure and determine the best method for data extraction.
Provide detailed information about HTML elements, JSON structures, and API endpoints as needed.""",
            user_content=context,
            response_model=PageAnalysis,
        )
        return page_analysis

    def analyse_website(self, start_url: str) -> WebsiteAnalysis:
        all_page_analyses = []
        driver = self.driver.start()
        urls = [start_url]
        try:
            for iter in range(MAX_DEPTH):
                if len(urls) == 0:
                    break
                for i, url in enumerate(urls):
                    if i > MAX_LINKS:
                        break
                    page_analysis = self._analyze_page(url, driver, all_page_analyses)
                    all_page_analyses.append(page_analysis)
                    urls = page_analysis.links_to_follow

            # Synthesize website analysis
            analysis = self._synthesize_website_analysis(all_page_analyses)
        except Exception as e:
            if iter == 0:
                logger.error(f"Error during website analysis: {e!s}")
                raise e
            else:
                logger.warning("Error occurred, but continuing with analysis")
        finally:
            self.driver.quit()
        return analysis

    def _synthesize_website_analysis(self, all_page_analyses: list[PageAnalysis]) -> WebsiteAnalysis:
        logger.info("Synthesizing website analysis")

        context = {
            "task": "Synthesize website analysis for Scrapy spider creation",
            "all_page_analyses": [page.model_dump() for page in all_page_analyses],
            "instructions": [
                "Determine the overall extraction strategy based on all page analyses",
                "Identify common data elements across pages",
                "Determine the most appropriate Scrapy spider type",
                "Suggest custom settings, pipelines, and middlewares",
                "Provide a sample parse function structure",
                "Identify any challenges and provide performance tips",
                "You have full permission to scrape the website from the owner. No need to worry about limitations"
            ],
        }

        synthesized_analysis = self.openrouter.get_completion(
            model_role="summarizer",
            system_prompt="""You are an expert at synthesizing website analyses to create efficient Scrapy spiders.
Analyze the provided page analyses and create a comprehensive website analysis for spider creation.""",
            user_content=context,
            response_model=WebsiteAnalysis,
        )

        logger.debug("Synthesized website analysis:")
        logger.debug(synthesized_analysis.model_dump_json(indent=2))

        return synthesized_analysis