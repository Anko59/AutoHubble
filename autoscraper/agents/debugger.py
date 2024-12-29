"""Debugger agent for testing spiders."""

import time
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from loguru import logger

from ..agents.navigator import NavigatorAgent
from ..config import SPIDER_TIMEOUT, MAX_DEBUGGER_LOOPS
from ..models import TestResult, PageAnalysis, WebsiteAnalysis
from ..utils.file_manager import SpiderFileManager
from ..utils.openrouter import OpenRouterClient
from ..utils.spider_runner import SpiderRunner


class DebuggerAgent:
    """Agent responsible for testing spiders and providing feedback."""

    def __init__(self, navigator: NavigatorAgent) -> None:
        """Initialize the debugger agent."""
        logger.info("Initializing DebuggerAgent")
        self.openrouter = OpenRouterClient()
        self.file_manager = SpiderFileManager()
        self.spider_runner = SpiderRunner()
        self.navigator = navigator

        # Initialize Jinja2 template environment
        self.template_env = Environment(loader=FileSystemLoader("autoscraper/prompts/templates"), autoescape=select_autoescape())

    def test_scraper(
        self, spider_path: Path, output_dir: Path, website_analysis: WebsiteAnalysis, debugging_history: list[dict]
    ) -> TestResult:
        """Test a spider and analyze its output.

        Args:
            spider_path: Path to the spider file

        Returns:
            TestResult with success status and recommendations
        """
        logger.info(f"Testing spider: {spider_path}")

        # Run the spider using spider runner
        start_time = time.time()

        try:
            success, stdout, stderr, items_scraped = self.spider_runner.run_spider(spider_path, output_dir, timeout=SPIDER_TIMEOUT)

            execution_time = time.time() - start_time

            if not success:
                return TestResult(
                    success=False, items_scraped=0, recommendations="Spider failed to run successfully", execution_time=execution_time
                )

        except Exception as e:
            logger.error(f"Error running spider: {str(e)}")
            return TestResult(
                success=False,
                items_scraped=0,
                recommendations=f"Failed to run spider: {str(e)}",
                execution_time=None,
            )

        # Analyze with LLM
        result = self._analyze_run(stdout, stderr, items_scraped, output_dir, website_analysis, debugging_history)

        # If the result suggests we need more information, gather it
        for _ in range(MAX_DEBUGGER_LOOPS):
            if not result.needs_more_info:
                break
            additional_info = self._gather_additional_info(result.url_to_analyze, result.analysis_instructions)
            if not additional_info:
                break
            result = self._analyze_run(stdout, stderr, items_scraped, output_dir, website_analysis, debugging_history, additional_info)

        if items_scraped == 0:
            result.success = False
            result.recommendations = "No items were scraped. " + result.recommendations

        return result

    def _gather_additional_info(self, url: str, instructions: str) -> PageAnalysis | None:
        """Gather additional information using the NavigatorAgent."""
        return self.navigator.analyze_specific_page(url, instructions)

    def _analyze_run(
        self,
        stdout: str,
        stderr: str,
        items_scraped: int,
        output_dir: Path,
        website_analysis: WebsiteAnalysis,
        debugging_history: list[dict],
        additional_info: PageAnalysis | None = None,
    ) -> TestResult:
        """Analyze spider run with LLM."""
        # Render context from template
        template = self.template_env.get_template("debugger_context.jinja2")
        context = template.render(
            website_analysis=website_analysis.model_dump(),
            debugging_history=debugging_history,
            stdout=stdout,
            stderr=stderr,
            items_scraped=items_scraped,
            spider_code=self.file_manager.get_project_content(output_dir),
            additional_info=additional_info.model_dump() if additional_info else None,
        )

        # Render system prompt from template
        template = self.template_env.get_template("debugger_system.jinja2")
        system_prompt = template.render(timeout_seconds=SPIDER_TIMEOUT)

        return self.openrouter.get_completion(
            model_role="debugger",
            system_prompt=system_prompt,
            user_content=context,
            response_model=TestResult,
        )
