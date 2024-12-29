"""Utility for running Scrapy spiders with proper output handling."""

import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from loguru import logger

from .file_manager import SpiderFileManager


class SpiderRunner:
    """Utility for running Scrapy spiders with proper output handling."""

    def __init__(self):
        """Initialize the spider runner."""
        self.file_manager = SpiderFileManager()

    def run_spider(self, spider_path: Path, output_dir: Path, timeout: Optional[int] = None) -> Tuple[bool, str, str, int]:
        """Run a Scrapy spider and capture output.

        Args:
            spider_path: Path to the spider project
            output_dir: Directory to store output files
            timeout: Optional timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            # Create output directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)

            # Set up environment
            env = os.environ.copy()
            env["PYTHONPATH"] = str(output_dir)

            # Get spider name from path
            spider_name = spider_path.stem

            # Build the command
            cmd = ["scrapy", "crawl", spider_name]

            # Run the spider with optional timeout
            logger.info(f"Running spider: {' '.join(cmd)}")
            process = subprocess.run(cmd, cwd=str(spider_path.parent), capture_output=True, text=True, env=env, timeout=timeout)

            stdout = process.stdout
            stderr = process.stderr

            # Save logs using file manager
            self.file_manager.save_logs(spider_name, stdout, stderr)

            logger.debug(f"Spider stdout: {stdout}")
            if stderr:
                logger.warning(f"Spider stderr: {stderr}")

            return True, stdout, stderr, self.count_scraped_items(output_dir)

        except subprocess.TimeoutExpired as e:
            stdout = str(e.stdout) if e.stdout else ""
            stderr = str(e.stderr) if e.stderr else ""
            logger.warning(f"Spider timed out after {timeout} seconds")
            self.file_manager.save_logs(spider_name, stdout, stderr)
            return False, stdout, stderr, self.count_scraped_items(output_dir)

        except Exception as e:
            logger.error(f"Error running spider: {str(e)}")
            return False, "", str(e), 0

    def count_scraped_items(self, output_dir: Path) -> int:
        """Count the number of items scraped from output file."""
        output_file = output_dir / "output.json"
        if not output_file.exists():
            return 0

        try:
            with open(output_file) as f:
                return len(f.readlines())
        except Exception as e:
            logger.error(f"Error counting scraped items: {e}")
            return 0
