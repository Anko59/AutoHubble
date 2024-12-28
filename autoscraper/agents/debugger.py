"""Debugger agent for testing spiders."""

import os
import time
import subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from loguru import logger
from pydantic import BaseModel, Field

from ..utils.file_manager import SpiderFileManager
from ..utils.openrouter import OpenRouterClient
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
        self.template_env = Environment(
            loader=FileSystemLoader("autoscraper/prompts/templates"),
            autoescape=select_autoescape()
        )

    def test_scraper(self, spider_path: Path, output_dir: Path, website_analysis: WebsiteAnalysis, debugging_history: list[dict]) -> TestResult:
        """Test a spider and analyze its output.

        Args:
            spider_path: Path to the spider file

        Returns:
            TestResult with success status and recommendations
        """
        logger.info(f"Testing spider: {spider_path}")

        # Get spider name from file
        spider_name = self._get_spider_name(spider_path, output_dir)
        if not spider_name:
            return TestResult(
                success=False,
                items_scraped=0,
                recommendations=f"Could not determine spider name from spider path {spider_path}",
            )

        # Run the spider
        try:
            # Run scrapy from the spider's project directory
            project_dir = output_dir
            env = os.environ.copy()
            env["PYTHONPATH"] = str(output_dir)

            timeout_seconds = SPIDER_TIMEOUT

            start_time = time.time()
            process = subprocess.run(
                ["scrapy", "crawl", spider_name],
                cwd=project_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout_seconds,
            )

            stdout = str(process.stdout)
            stderr = str(process.stderr)
            timed_out = False
            logger.debug(f"Spider execution stdout: {stdout}")
            logger.debug(f"Spider execution stderr: {stderr}")

        except subprocess.TimeoutExpired as e:
            stdout = e.stdout if e.stdout else ""
            stderr = e.stderr if e.stderr else ""
            timed_out = True
            logger.info(f"Spider execution timed out after {timeout_seconds} seconds, which is expected")

        except Exception as e:
            logger.error(f"Error running spider: {str(e)}")
            return TestResult(
                success=False,
                items_scraped=0,
                recommendations=f"Failed to run spider: {str(e)}",
                execution_time=None,
            )

        execution_time = time.time() - start_time
        if timed_out:
            stdout += f"\n\nSpider execution timed out after {execution_time} seconds"

        # Save logs
        self.file_manager.save_logs(spider_name, stdout, stderr)

        # Count items
        items_scraped = self._count_items(output_dir)

        # Analyze with LLM
        result = self._analyze_run(stdout, stderr, items_scraped, output_dir, website_analysis, debugging_history)

        if items_scraped == 0:
            result.success = False
            result.recommendations = "No items were scraped. " + result.recommendations

        return result

    def _analyze_run(self, stdout: str, stderr: str, items_scraped: int, output_dir: Path, website_analysis: WebsiteAnalysis, debugging_history: list[dict]) -> TestResult:
        """Analyze spider run with LLM."""
        # Render context from template
        template = self.template_env.get_template("debugger_context.jinja2")
        context = template.render(
            website_analysis=website_analysis.model_dump(),
            debugging_history=debugging_history,
            stdout=stdout,
            stderr=stderr,
            items_scraped=items_scraped,
            spider_code=self.file_manager.get_project_content(output_dir)
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


    def _get_spider_name(self, spider_path: Path, output_dir: Path) -> str:
        """Extract spider name from file."""
        try:
            path = output_dir / spider_path
            content = path.read_text()
            for line in content.split("\n"):
                if "name = " in line:
                    return line.split("=")[1].strip().strip("\"'")
            return None
        except Exception as e:
            logger.error(f"Error reading spider file: {str(e)}")
            return None

    def _count_items(self, spider_dir: Path) -> int:
        """Count scraped items."""
        try:
            items_file = spider_dir / "items.json"
            if not items_file.exists():
                return 0
            return sum(1 for _ in items_file.open())
        except Exception as e:
            logger.error(f"Error counting items: {str(e)}")
            return 0
