# AutoScraper: AI Multi-Agent System for Scrapy

An intelligent multi-agent system that generates Python Scrapy scrapers based on user inputs. The system uses AI agents to analyze websites, generate navigation code, and create robust scrapers.

## Technical Overview

The system is built around three core components:

1. **Navigator Agent**: Analyzes website structure using Selenium and ChromeDriver
2. **Generator Agent**: Creates Scrapy spiders based on analysis
3. **Debugger Agent**: Tests and improves scrapers through feedback loops

## Key Design Choices

### Architecture
The system follows a modular architecture with clear separation of concerns:
- **Agents**: Specialized components for specific tasks
- **Utils**: Reusable utility functions
- **Models**: Data structures for system communication
- **Prompts**: Templates for AI interactions

### Technology Stack
- **Scrapy Zyte API**: For reliable web scraping
- **Selenium/ChromeDriver**: For website navigation and analysis
- **OpenRouter API**: For AI-powered code generation
- **Pydantic**: For structured data validation
- **Loguru**: For comprehensive logging

## Project Structure

```
autoscraper/
├── agents/             # AI agents for different tasks
│   ├── navigator.py    # Website navigation agent
│   ├── generator.py    # Scraper code generation agent
│   └── debugger.py     # Testing and debugging agent
├── base_spider/        # Base Scrapy project template
│   ├── items.py
│   ├── pipelines.py
│   └── settings.py
├── config.py          # Configuration settings
├── models.py          # Data models
├── utils/             # Utility functions
│   ├── chrome_driver.py # Browser automation
│   ├── html_parser.py  # HTML parsing
│   ├── openrouter.py   # OpenRouter API integration
│   └── file_manager.py # File operations
│   └── spider_runner.py # Scrapy spider runner
├── prompts/           # Prompt templates for AI agents
│   └── templates/
│       ├── page_analysis.jinja2
│       └── website_analysis.jinja2
|       └── ...
├── requirements.txt   # Dependencies
├── autoscraper.py     # Main AutoScraper class
└── example.py         # Example usage
```

## Core Workflow

The system follows a structured workflow to ensure quality and iterative refinement:

1. **Website Analysis**
   - Navigates website using Selenium
   - Identifies data sources and extraction methods
   - Generates detailed analysis report

2. **Scraper Generation**
   - Creates Scrapy spider based on analysis
   - Implements navigation and extraction logic
   - Sets up pipelines for data processing

3. **Testing and Debugging**
   - Executes spider with timeout for testing
   - Analyzes output for errors and missing data
   - Iteratively improves spider based on feedback

4. **Spider Execution**
   - Runs generated spider without timeout
   - Handles logging and error reporting
   - Saves output to designated location

## Model Choices

The system uses different AI models for specific tasks:

| Agent       | Primary Model          | Fallback Models               |
|-------------|------------------------|-------------------------------|
| Navigator   | gemini-2-flash         | gpt-4o-mini, gemini-flash-1-5 |
| Generator   | gpt-4o                 | gemini-exp, claude-3.5-sonnet |
| Debugger    | gemini-2-flash-thinking| o1-mini, qwq                  |

## Development Guidelines

1. **Code Structure**
   - Keep files under 300 lines
   - Maintain clear separation of concerns
   - Use type hints for all function definitions

2. **Environment Management**
   - Use Poetry for dependency management
   - Configure environment variables in .env
   - Use Docker for containerization

3. **Code Quality**
   - Use Ruff for linting and formatting
   - Follow PEP 8 style guide
   - Maintain comprehensive logging

## Example Usage

```python
from autoscraper import AutoScraper

scraper = AutoScraper()
scraper.analyze_website("https://example.com")
scraper.set_target_fields({
    "product_name": "str",
    "price": "number",
    "availability": "boolean"
})
scraper.generate()
scraper.run()
```

## License

MIT License
