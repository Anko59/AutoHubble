"""Generator agent for creating Scrapy spiders."""

from pathlib import Path

from loguru import logger

from ..config import MAX_ACTIONS
from ..models import ActionMemory, GeneratorAction
from ..utils.file_manager import SpiderFileManager
from ..utils.openrouter import OpenRouterClient
from .debugger import TestResult
from .navigator import WebsiteAnalysis


class GeneratorAgent:
    """Agent responsible for generating Scrapy spider code."""

    def __init__(self) -> None:
        """Initialize the generator agent."""
        logger.info("Initializing GeneratorAgent")
        self.openrouter = OpenRouterClient()
        self.file_manager = SpiderFileManager()

    def generate_spider(
        self,
        website_structure: WebsiteAnalysis,
        target_fields: dict[str, str],
        spider_name: str,
        debug_result: TestResult = None,
        output_dir: Path = None,
    ) -> None:
        """Generate a Scrapy spider based on website analysis.

        Args:
            website_structure: Analyzed website structure
            target_fields: Fields to extract and their types
            spider_name: Name for the spider
            debug_result: Optional feedback from previous test run
            output_dir: Directory to save the spider

        Returns:
            Path to the generated spider file
        """
        previous_actions = []
        for _ in range(MAX_ACTIONS):
            action = self._get_action(
                website_structure,
                target_fields,
                spider_name,
                debug_result,
                output_dir,
                previous_actions
            )
            output = self.file_manager.implement_action(output_dir, action)
            previous_actions.append(
                ActionMemory(
                    action=action,
                    feedback=output,
                )
            )

            if action.is_final and any([fb.success for fb in output]):
                break

    def _get_action(
        self,
        website_structure: WebsiteAnalysis,
        target_fields: dict[str, str],
        spider_name: str,
        debug_result: TestResult = None,
        output_dir: Path = None,
        previous_actions: list[ActionMemory] | None = None,
    ) -> GeneratorAction:
        logger.info("Starting spider generation")

        # Prepare context for code generation
        context = {
            "website_structure": website_structure.model_dump(),
            "current_project_code": self.file_manager.get_project_content(output_dir),
            "target_fields": target_fields,
            "spider_name": spider_name,
            "previous_actions": [action.model_dump() for action in previous_actions],
            "requirements": [
                "Must use scrapy.Spider as base class",
                "Must implement parse method",
                "Must handle pagination if available",
                "Must use loguru for logging",
                "ONLY FILL THE DEMANDED JSON",
                "DO NOT PROVIDE ANY ADDITIONAL TEXT, respond in JSON format",
                "Otherwise the parsing will fail and this will be all for nothing"
            ],
        }

        # Add debug feedback if available
        if debug_result:
            context["debug_feedback"] = debug_result.model_dump()
            logger.info("Including debug feedback in generation context")

        # Generate spider code
        action = self.openrouter.get_completion(
            model_role="generator",
            system_prompt=(
                "You are an expert at generating Scrapy spiders. "
                "Generate a spider that extracts data from the website using "
                "the most appropriate method based on the website structure analysis."
            ),
            user_content=context,
            response_model=GeneratorAction,
        )

        return action
