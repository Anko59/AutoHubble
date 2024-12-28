"""File management utilities for spider operations."""

import os
import shutil
from pathlib import Path

from loguru import logger
from unidiff import PatchSet

from ..models import ActionExecutionFeedBack, GeneratorAction


def apply_diff(file_path, diff_string: str):
    diff_string = diff_string.replace("```diff\n", "")
    diff_string = diff_string.replace("```pyhton\n", "")
    diff_string = diff_string.replace("```\n", "")
    diff_string = diff_string.replace("```", "")

    # Parse the diff string
    logger.info(f"Applying diff: {diff_string}")
    try:
        patch_set = PatchSet.from_string(diff_string)

        # Read the original file content
        with open(file_path, "r") as file:
            original_content = file.read()

        # Apply the patch
        patched_content = original_content
        for patched_file in patch_set:
            for hunk in patched_file:
                try:
                    patched_content = hunk.apply(patched_content)
                except Exception as e:
                    logger.error(f"Failed to apply hunk: {hunk}")
                    logger.error(e)
    except Exception as e:
        logger.error(f"Failed to apply diff: {diff_string}")
        logger.error(e)
        patched_content = diff_string

    # Write the patched content back to the file
    with open(file_path, "w") as file:
        file.write(patched_content)

    logger.info(f"Diff applied successfully to {file_path}")


class SpiderFileManager:
    """Manages file operations for spider projects."""

    def setup_project(self, base_path: Path, output_path: Path, spider_name: str) -> Path:
        """Set up a new spider project by copying base files.

        Args:
            base_path: Path to base spider files
            output_path: Path to create new project
        """
        logger.info(f"Setting up spider project in {output_path}")
        shutil.copytree(base_path, output_path, dirs_exist_ok=True)

        # Rename base_spider folder to new spider name
        base_spider_path = output_path / "base_spider"
        new_spider_path = output_path / output_path.name
        base_spider_path.rename(new_spider_path)

        # Update module paths in settings
        settings_path = new_spider_path / "settings.py"
        if settings_path.exists():
            content = settings_path.read_text()
            content = (
                content.replace(
                    'SPIDER_MODULES = ["base_spider.spiders"]',
                    f'SPIDER_MODULES = ["{output_path.name}.spiders"]',
                )
                .replace(
                    'NEWSPIDER_MODULE = "base_spider.spiders"',
                    f'NEWSPIDER_MODULE = "{output_path.name}.spiders"',
                )
                .replace('BOT_NAME = "base_spider"', f'BOT_NAME = "{spider_name}"')
                .replace(
                    'ZYTE_API_KEY = "YOUR_ZYTE_API_KEY"',
                    f"""ZYTE_API_KEY = "{os.getenv("ZYTE_API_KEY")}" """,
                )
            )
            settings_path.write_text(content)

        # Update scrapy.cfg
        cfg_path = output_path / "scrapy.cfg"
        cfg_content = cfg_path.read_text()
        cfg_content = cfg_content.replace("base_spider", output_path.name)
        cfg_path.write_text(cfg_content)

        spider_file_path = new_spider_path / "spiders/spider.py"
        if spider_file_path.exists():
            new_spider_file_path = new_spider_path / f"spiders/{spider_name}.py"
            spider_file_path.rename(new_spider_file_path)

        spider_content = new_spider_file_path.read_text()
        spider_content = spider_content.replace("BasespiderSpider", f"{spider_name.capitalize()}Spider")
        spider_content = spider_content.replace('name = "base_spider"', f'name = "{spider_name}"')
        new_spider_file_path.write_text(spider_content)

        return new_spider_file_path

    def save_logs(self, spider_name: str, stdout: str, stderr: str) -> None:
        """Save spider run logs.

        Args:
            spider_name: Name of the spider
            stdout: Standard output from spider run
            stderr: Standard error from spider run
        """
        log_dir = Path("output/logs") / spider_name
        log_dir.mkdir(parents=True, exist_ok=True)

        (log_dir / "stdout.log").write_text(stdout)
        (log_dir / "stderr.log").write_text(stderr)
        logger.debug(f"Logs saved to {log_dir}")

    def _handle_create_action(self, output_dir: Path, action: GeneratorAction) -> ActionExecutionFeedBack:
        """Handle create action."""
        file_path = output_dir / action.file

        if file_path.exists():
            logger.warning(f"File {file_path} already exists. Skipping.")
            return ActionExecutionFeedBack(
                success=False,
                message=f"File {file_path} already exists. Skipping.",
            )

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(action.content)
        logger.debug(f"Created file {file_path}")
        return ActionExecutionFeedBack(
            success=True,
            message=f"Created file {file_path}",
        )

    def _handle_edit_action(self, output_dir: Path, action: GeneratorAction) -> ActionExecutionFeedBack:
        """Handle edit action."""
        file_path = output_dir / action.file

        if not action.diff:
            logger.warning(f"No diff for file {file_path}. Skipping.")
            return ActionExecutionFeedBack(
                success=False,
                message=f"No diff for file {file_path}. Skipping.",
            )
        if not file_path.exists():
            logger.warning(f"File {file_path} does not exist. Skipping.")
            return ActionExecutionFeedBack(
                success=False,
                message=f"File {file_path} does not exist. Skipping.",
            )
        apply_diff(file_path, action.diff)
        logger.debug(f"Edited file {file_path}")
        return ActionExecutionFeedBack(
            success=True,
            message=f"Edited file {file_path}",
        )

    def _handle_delete_action(self, output_dir: Path, action: GeneratorAction) -> ActionExecutionFeedBack:
        """Handle delete action."""
        file_path = output_dir / action.file
        if not file_path.exists():
            logger.warning(f"File {file_path} does not exist. Skipping.")
            return ActionExecutionFeedBack(
                success=False,
                message=f"File {file_path} does not exist. Skipping.",
            )
        file_path.unlink()
        logger.debug(f"Deleted file {file_path}")

        return ActionExecutionFeedBack(
            success=True,
            message=f"Deleted file {file_path}",
        )

    def _handle_overwrite_action(self, output_dir: Path, action: GeneratorAction) -> ActionExecutionFeedBack:
        """Handle overwrite action."""
        file_path = output_dir / action.file
        if not file_path.exists():
            logger.warning(f"File {file_path} does not exist. Skipping.")
            return ActionExecutionFeedBack(
                success=False,
                message=f"File {file_path} does not exist. Skipping.",
            )
        file_path.write_text(action.content)
        logger.debug(f"Overwritten file {file_path}")
        return ActionExecutionFeedBack(
            success=True,
            message=f"Overwritten file {file_path}",
        )

    def _handle_append_action(self, output_dir: Path, action: GeneratorAction) -> ActionExecutionFeedBack:
        """Handle append action."""
        file_path = output_dir / action.file
        if not file_path.exists():
            logger.warning(f"File {file_path} does not exist. Skipping.")
            return ActionExecutionFeedBack(
                success=False,
                message=f"File {file_path} does not exist. Skipping.",
            )
        file_path.write_text(file_path.read_text() + action.content)
        logger.debug(f"Appended to file {file_path}")

        return ActionExecutionFeedBack(
            success=True,
            message=f"Appended to file {file_path}",
        )

    def implement_action(self, output_dir: Path, action: GeneratorAction) -> list[ActionExecutionFeedBack]:
        """Implement a generator action."""
        feedbacks = []
        for file_action in action.actions:
            if file_action.action_type == "create":
                feedbacks.append(self._handle_create_action(output_dir, file_action))
            elif file_action.action_type == "edit":
                feedbacks.append(self._handle_edit_action(output_dir, file_action))
            elif file_action.action_type == "delete":
                feedbacks.append(self._handle_delete_action(output_dir, file_action))
            elif file_action.action_type == "overwrite":
                feedbacks.append(self._handle_overwrite_action(output_dir, file_action))
            elif file_action.action_type == "append":
                feedbacks.append(self._handle_append_action(output_dir, file_action))
            else:
                logger.warning(f"Unknown action type {file_action.type}. Skipping.")
                feedbacks.append(
                    ActionExecutionFeedBack(
                        success=False,
                        message=f"Unknown action type {file_action.type}. Skipping.",
                    )
                )
        return feedbacks

    def get_project_content(self, project_dir: Path) -> list[dict[str, str]]:
        """Get the content of .py and .cfg files in a project directory."""
        content = []
        for path in project_dir.glob("**/*"):
            if path.is_file() and path.suffix in [".py", ".cfg"]:
                try:
                    relative_path = path.relative_to(project_dir)
                    content.append(
                        {
                            "path": str(relative_path),
                            "content": path.read_text(encoding="utf-8"),
                        }
                    )
                except Exception as e:
                    logger.error(f"Error reading file {path}: {str(e)}")
        return content
