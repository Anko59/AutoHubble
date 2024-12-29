"""Configuration settings for AutoScraper."""

from pathlib import Path
from enum import Enum

# OpenRouter configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/Anko59/AutoHubble",
    "X-Title": "AutoHubble",
}


class Provider(Enum):
    GOOGLE = "Google"
    OPENAI = "OpenAI"
    GOOGLE_AI_STUDIO = "Google AI Studio"
    ANTHROPIC = "Anthropic"


class Model:
    def __init__(
        self,
        name: str,
        context_length: int,
        description: str,
        structured_output: bool,
        pydantic_output: bool,
        providers: list[Provider] | None = None,
        retries: int = 3,
    ):
        self.name = name
        self.context_length = context_length
        self.description = description
        self.structured_output = structured_output
        self.pydantic_output = pydantic_output
        self.providers = providers
        self.retries = retries


# AI model configurations
MODELS: dict[str, Model] = {
    "claude-3.5-sonnet": Model(
        name="anthropic/claude-3.5-sonnet:beta",
        context_length=200000,
        description="Claude 3.5 Sonnet",
        structured_output=True,
        pydantic_output=False,
        providers=[Provider.ANTHROPIC],
    ),
    "gpt-4o": Model(
        name="openai/gpt-4o-2024-11-20",
        context_length=128000,
        description="GPT-4o",
        structured_output=True,
        pydantic_output=True,
        providers=[Provider.OPENAI],
    ),
    "gpt-4o-mini": Model(
        name="openai/gpt-4o-mini",
        context_length=128000,
        description="GPT-4o Mini",
        structured_output=True,
        pydantic_output=True,
        providers=[Provider.OPENAI],
    ),
    "qwq": Model(
        name="qwen/qwq-32b-preview",
        context_length=32000,
        description="Qwen QWQ 32B Preview",
        structured_output=False,
        pydantic_output=False,
    ),
    "o1-mini": Model(
        name="openai/o1-mini",
        context_length=128000,
        description="O1 Mini",
        structured_output=False,
        pydantic_output=False,
        providers=[Provider.OPENAI],
    ),
    "gemini-2-flash": Model(
        name="google/gemini-2.0-flash-exp:free",
        context_length=1000000,
        description="Gemini 2.0 Flash Experimental",
        structured_output=True,
        pydantic_output=True,
        providers=[Provider.GOOGLE],
        retries=5,
    ),
    "gemini-exp": Model(
        name="google/gemini-exp-1206:free",
        context_length=2000000,
        description="Gemini Experimental 1206",
        structured_output=True,
        pydantic_output=True,
        providers=[Provider.GOOGLE, Provider.GOOGLE_AI_STUDIO],
    ),
    "gemini-2-flash-thinking": Model(
        name="google/gemini-2.0-flash-thinking-exp:free",
        context_length=40000,
        description="Gemini 2.0 Flash Thinking Experimental",
        structured_output=False,
        pydantic_output=False,
        providers=[Provider.GOOGLE, Provider.GOOGLE_AI_STUDIO],
    ),
    "gemini-flash-1-5": Model(
        name="google/gemini-flash-1.5",
        context_length=2000000,
        description="Gemini Flash 1.5",
        structured_output=True,
        pydantic_output=True,
        providers=[Provider.GOOGLE, Provider.GOOGLE_AI_STUDIO],
    ),
    "deepseek-v3": Model(
        name="deepseek/deepseek-chat",
        context_length=64000,
        description="DeepSeek V3",
        structured_output=True,
        pydantic_output=False,
    ),
    "llama-3.3-70b": Model(
        name="meta-llama/llama-3.3-70b-instruct",
        context_length=131000,
        description="Llama 3.3 70B",
        structured_output=True,
        pydantic_output=False,
    ),
    # Add more models as needed
}

# Model choices with fallbacks
MODEL_CHOICES: dict[str, list[str]] = {
    "navigator": ["gemini-2-flash", "gpt-4o-mini", "gemini-flash-1-5", "llama-3.3-70b"],
    "generator": ["deepseek-v3", "gemini-exp", "claude-3.5-sonnet", "gpt-4o"],
    "debugger": ["claude-3.5-sonnet", "gemini-2-flash-thinking", "qwq", "o1-mini"],
    "structurer": ["gemini-flash-1-5"],
    "summarizer": ["gemini-2-flash-thinking", "gpt-4o", "o1-mini", "qwq"],
}


# Base paths
PROJECT_ROOT = Path(__file__).parent
BASE_SPIDER_PATH = PROJECT_ROOT / "base_spider"
OUTPUT_PATH = PROJECT_ROOT.parent / "output"

# Spider settings
DEFAULT_SPIDER_SETTINGS = {
    "CONCURRENT_REQUESTS": 16,
    "DOWNLOAD_DELAY": 1,
    "ROBOTSTXT_OBEY": True,
    "LOG_LEVEL": "INFO",
}

# Navigation settings
NAVIGATION_TIMEOUT = 30  # seconds
SCROLL_PAUSE_TIME = 2  # seconds
MAX_DEPTH = 3
MAX_LINKS = 5

# Generation settings
MAX_FIELDS = 20  # Maximum number of fields per scraper
CODE_STYLE = "black"  # Code formatting style
MAX_ACTIONS = 20  # Maximum number of actions per iteration for the geneartor
MAX_ITERS = 10  # Maximum number of iterations for the generator

# Output settings
DEFAULT_OUTPUT_FORMAT = "json"
SAVE_LOGS = True

# Debbuger settings
SPIDER_TIMEOUT = 120  # seconds
MAX_DEBUGGER_LOOPS = 1  # Maximum number of debugger/navigator loops
