"""Debugger agent for testing spiders."""

import time
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from loguru import logger
from pydantic import BaseModel, Field

from ..utils.file_manager import SpiderFileManager
from ..utils.openrouter import OpenRouterClient
from ..utils.spider_runner import SpiderRunner
from ..config import SPIDER_TIMEOUT
from ..models import WebsiteAnalysis


class TestResult(BaseModel):
    """Result of spider test run with recommendations."""

    success: bool = Field(description="Whether the test was successful")
    items_scraped: int = Field(description="Number of items scraped")
    recommendations: str = Field(description="Recommendations for improving the spider")


class DebuggerAgent:
    """Agent responsible for testing spiders and providing feedback."""

    def __init__(self) -> None:
        """Initialize the debugger agent."""
        logger.info("Initializing DebuggerAgent")
        self.openrouter = OpenRouterClient()
        self.file_manager = SpiderFileManager()

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
        spider_runner = SpiderRunner()
        start_time = time.time()

        try:
            success, stdout, stderr, items_scraped = spider_runner.run_spider(spider_path, output_dir, timeout=SPIDER_TIMEOUT)

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

        if items_scraped == 0:
            result.success = False
            result.recommendations = "No items were scraped. " + result.recommendations

        return result

    def _analyze_run(
        self,
        stdout: str,
        stderr: str,
        items_scraped: int,
        output_dir: Path,
        website_analysis: WebsiteAnalysis,
        debugging_history: list[dict],
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
