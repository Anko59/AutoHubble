# AutoScraper: AI Multi-Agent System for Scrapy

An intelligent multi-agent system that generates Python Scrapy scrapers based on user inputs. The system uses AI agents to analyze websites, generate navigation code, and create robust scrapers.

## Features

- AI-powered website analysis and scraper generation
- Integration with Scrapy Zyte API for reliable scraping
- Multi-agent architecture for specialized tasks
- Automated scraper testing and debugging
- JSON data pipeline for structured output

## Setup Instructions

1. **Install Poetry**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install Dependencies**
   ```bash
   poetry install
   ```

3. **Environment Setup**
   - Copy `.env.example` to `.env`
   ```bash
   cp .env.example .env
   ```
   - Add your API keys to `.env`:
     - Get a Zyte API key from https://www.zyte.com/
     - Get an OpenRouter API key from https://openrouter.ai/
   ```
   ZYTE_API_KEY=your_zyte_api_key_here
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

4. **Docker Setup** (Optional)
   ```bash
   docker build -t autoscraper .
   docker run -it --env-file .env autoscraper
   ```

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
└── config.py          # Configuration settings
```

## Using the AI Multi-Agent System

1. **Initialize a New Scraping Task**
   ```python
   from autoscraper import AutoScraper
   
   scraper = AutoScraper()
   scraper.analyze_website("https://example.com")
   ```

2. **Define Scraping Requirements**
   ```python
   fields = {
       "product_name": "text",
       "price": "number",
       "availability": "boolean"
   }
   scraper.set_target_fields(fields)
   ```

3. **Generate and Run Scraper**
   ```python
   scraper.generate()
   scraper.run()
   ```

## Example Input/Output

Input:
```python
{
    "website": "https://example.com",
    "fields": ["name", "price", "stock"],
    "output_format": "json"
}
```

Output:
```json
{
    "items": [
        {
            "name": "Product 1",
            "price": 29.99,
            "stock": true
        },
        {
            "name": "Product 2",
            "price": 49.99,
            "stock": false
        }
    ]
}
```

## Configuration

The system behavior can be customized through `config.py`:

- **AI Models**: Configure which models to use for each agent
- **Spider Settings**: Adjust scraping parameters
- **Navigation Settings**: Customize website navigation behavior
- **Output Settings**: Configure data output format and logging

## Development Guidelines

- Follow PEP 8 style guide
- Use type hints for all function definitions
- Keep files under 300 lines
- Run Ruff linter before committing changes
- Test scrapers thoroughly with different websites

## Environment Variables

Required environment variables in `.env`:

- `ZYTE_API_KEY`: Your Zyte API key for web scraping
- `OPENROUTER_API_KEY`: Your OpenRouter API key for AI models

## License

MIT License