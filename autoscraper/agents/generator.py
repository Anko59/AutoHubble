"""Generator agent for creating Scrapy spiders."""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

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
        
        # Initialize Jinja2 template environment
        self.template_env = Environment(
            loader=FileSystemLoader("autoscraper/prompts/templates"),
            autoescape=select_autoescape()
        )

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

        # Render context from template
        template = self.template_env.get_template("generator_user_context.jinja2")
        context = template.render(
            website_structure=website_structure.model_dump(),
            current_project_code=self.file_manager.get_project_content(output_dir),
            target_fields=target_fields,
            spider_name=spider_name,
            previous_actions=[action.model_dump() for action in previous_actions],
            debug_feedback=debug_result.model_dump() if debug_result else None
        )
        
        # Render requirements from template
        template = self.template_env.get_template("generator_context.jinja2")
        requirements = template.render().splitlines()
        context = {**context, "requirements": requirements}

        # Add debug feedback if available
        if debug_result:
            context["debug_feedback"] = debug_result.model_dump()
            logger.info("Including debug feedback in generation context")

        # Render system prompt from template
        template = self.template_env.get_template("generator_system.jinja2")
        system_prompt = template.render()
        
        # Generate spider code
        action = self.openrouter.get_completion(
            model_role="generator",
            system_prompt=system_prompt,
            user_content=context,
            response_model=GeneratorAction,
        )

        return action
