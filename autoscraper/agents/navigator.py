"""Navigator agent for website analysis using Selenium and LLM."""

import time
from urllib.parse import urljoin, urlparse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from loguru import logger

from ..config import MAX_DEPTH, MAX_LINKS
from ..models import PageAnalysis, WebsiteAnalysis
from ..utils.chrome_driver import ChromeDriver
from ..utils.html_parser import HTMLParser
from ..utils.openrouter import OpenRouterClient


class NavigatorAgent:
    """Agent responsible for analyzing websites and gathering structural information."""

    def __init__(self) -> None:
        """Initialize the navigator agent."""
        logger.info("Initializing NavigatorAgent")

        self.openrouter = OpenRouterClient()
        self.driver = ChromeDriver()
        self.html_parser = HTMLParser()
        self.base_url: str | None = None

        # Initialize Jinja2 template environment
        self.template_env = Environment(loader=FileSystemLoader("autoscraper/prompts/templates"), autoescape=select_autoescape())

    @staticmethod
    def _get_core_base_url(url: str) -> str:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return base_url

    def _analyze_page(self, url: str, driver, all_page_analyses: list[PageAnalysis]) -> PageAnalysis:
        """Analyze a webpage to identify its structure and data elements.

        Args:
            url: The URL to analyze

        Returns:
            WebsiteStructure containing the analysis results
        """
        if self.base_url is None:
            self.base_url = self._get_core_base_url(url)
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

        # Render context from template
        template = self.template_env.get_template("navigator_context.jinja2")
        context = template.render(
            previous_requests=[page.model_dump() for page in all_page_analyses],
            page_source=page_source,
            network_requests=network_requests,
            json_data=json_data,
        )

        # Log the context for debugging
        logger.debug("Analysis context:")
        logger.debug(f"Page source length: {len(page_source)}")
        logger.debug(f"Found {len(network_requests)} network requests")

        # Render system prompt from template
        template = self.template_env.get_template("page_analysis.jinja2")
        system_prompt = template.render()

        page_analysis = self.openrouter.get_completion(
            model_role="navigator",
            system_prompt=system_prompt,
            user_content=context,
            response_model=PageAnalysis,
        )
        return page_analysis

    def analyse_website(self, start_url: str) -> WebsiteAnalysis:
        all_page_analyses: list[PageAnalysis] = []
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

        # Render context from template
        template = self.template_env.get_template("website_analysis_context.jinja2")
        context = template.render(all_page_analyses=[page.model_dump() for page in all_page_analyses])

        # Render system prompt from template
        template = self.template_env.get_template("website_analysis.jinja2")
        system_prompt = template.render()

        synthesized_analysis = self.openrouter.get_completion(
            model_role="summarizer",
            system_prompt=system_prompt,
            user_content=context,
            response_model=WebsiteAnalysis,
        )

        logger.debug("Synthesized website analysis:")
        logger.debug(synthesized_analysis.model_dump_json(indent=2))

        return synthesized_analysis
