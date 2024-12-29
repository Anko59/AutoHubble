from typing import Literal

import jsonref
from pydantic import BaseModel, Field


def resolve_jsonref(obj):
    """Recursively resolve jsonref.JsonRef objects."""
    if isinstance(obj, dict):
        # If it's a dictionary, resolve its values
        return {k: resolve_jsonref(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # If it's a list, resolve its elements
        return [resolve_jsonref(item) for item in obj]
    elif isinstance(obj, jsonref.JsonRef):
        # If it's a JsonRef, return its resolved value
        return obj.resolved
    else:
        # Otherwise, just return the object as is
        return obj


class ExtendedBaseModel(BaseModel):
    @classmethod
    def model_json_schema(cls, *args, **kwargs):
        # Generate the base schema
        schema = super().model_json_schema(*args, **kwargs)
        schema = jsonref.replace_refs(schema)
        # Resolve the references
        schema = resolve_jsonref(schema)
        # Remove the "$defs" key if it exists
        schema.pop("$defs", None)
        return schema

    class Config:
        json_schema_extra = {"additionalProperties": False}


class HTMLElement(ExtendedBaseModel):
    selector: str = Field(..., description="CSS selector or XPATH for the HTML element")
    sample_value: str = Field(..., description="Sample value extracted from this element, in html")
    description: str = Field(..., description="Description of what this element represents")


class JSONElement(ExtendedBaseModel):
    key_path: str = Field(..., description="JSON path to the element")
    sample_value: str = Field(..., description="Sample value extracted from this JSON element")
    description: str = Field(..., description="Description of what this JSON element represents")
    xpath: str = Field(..., description="XPATH for the script element containing the JSON")


class DataElement(ExtendedBaseModel):
    type: Literal["html", "json", "api", "computed"] = Field(..., description="Type of data element")
    name: str = Field(..., description="Name of the data element")
    extraction_method: str = Field(..., description="Method to extract this data (e.g., CSS selector, XPATH, JSON path, or API endpoint)")
    sample_value: str = Field(..., description="Sample value for this data element")
    description: str = Field(..., description="Description of what this data element represents")


class PaginationInfo(ExtendedBaseModel):
    method: Literal["html_link", "api_param", "url_modification", "infinite_scroll"] = Field(..., description="Method used for pagination")
    selector_or_param: str = Field(..., description="Selector or parameter used for pagination")
    max_pages: int = Field(..., description="Maximum number of pages to scrape, or -1 if unknown")


class APIEndpoint(ExtendedBaseModel):
    url: str = Field(..., description="URL of the API endpoint")
    method: Literal["GET", "POST"] = Field(..., description="HTTP method for the API call")
    params: str = Field(default_factory=dict, description="Query parameters for the API call")
    headers: str = Field(default_factory=dict, description="Headers for the API call")


class Token(ExtendedBaseModel):
    token: str = Field(..., description="Token for authentication")
    expires_at: str = Field(..., description="Expiration time for the token")
    value: str = Field(..., description="Value of the token")
    selector: str = Field(..., description="Selector or method to obtain the token")
    token_type: str = Field(..., description="Type of token (e.g., 'localStorage', 'cookie', 'meta', 'script', 'data-attribute')")


class PageAnalysis(ExtendedBaseModel):
    url: str = Field(..., description="URL of the analyzed page")
    title: str = Field(..., description="Title of the page")
    extraction_method: Literal["html", "json", "api", "mixed"] = Field(..., description="Primary method of data extraction for this page")
    html_elements: list[HTMLElement] = Field(..., description="List of html elements found on this page containg data")
    json_elements: list[JSONElement] = Field(..., description="List of json elements found on this page containg data")
    pagination_info: PaginationInfo = Field(..., description="Information about pagination on this page")
    api_endpoints: list[APIEndpoint] = Field(default_factory=list, description="List of API endpoints found on this page")
    javascript_required: bool = Field(..., description="Whether JavaScript is required to render the page content")
    dynamic_content: bool = Field(..., description="Whether the page contains dynamically loaded content")
    main_content_selector: str = Field(..., description="CSS selector for the main content area of the page")
    links_to_follow: list[str] = Field(default_factory=list, description="List of links to follow for further scraping")
    tokens: list[Token] = Field(default_factory=list, description="List of tokens found on this page")
    remarks: list[str] = Field(default_factory=list, description="Additional remarks or observations about the page")


class WebsiteAnalysis(ExtendedBaseModel):
    base_url: str = Field(..., description="Base URL of the website")
    spider_name: str = Field(..., description="Suggested name for the Scrapy spider")
    spider_type: Literal["CrawlSpider", "SitemapSpider", "CSVFeedSpider", "XMLFeedSpider"] = Field(
        ..., description="Type of Scrapy spider to use"
    )
    start_urls: list[str] = Field(..., description="List of URLs to start scraping from")
    custom_settings: str = Field(default_factory=dict, description="Custom settings for the Scrapy spider")
    tokens: list[Token] = Field(default_factory=list, description="List of tokens necessary for writing the spider")

    extraction_strategy: Literal["html", "json", "api", "mixed"] = Field(..., description="Overall strategy for data extraction")
    main_data_elements: list[DataElement] = Field(..., description="Main data elements to be extracted across the website")
    global_pagination: PaginationInfo = Field(..., description="Global pagination strategy for the website")

    api_endpoints: list[APIEndpoint] = Field(default_factory=list, description="List of important API endpoints for the website")
    javascript_handling: str = Field(..., description="Strategy for handling JavaScript-rendered content")

    item_structure: str = Field(..., description="Structure of the Scrapy Item to be used")
    pipeline_recommendations: list[str] = Field(..., description="Recommended Scrapy pipelines")
    middleware_recommendations: list[str] = Field(..., description="Recommended Scrapy middlewares")

    crawl_rules: str = Field(default_factory=list, description="Crawl rules for CrawlSpider")
    sitemap_urls: list[str] = Field(default_factory=list, description="Sitemap URLs for SitemapSpider")

    challenges: list[str] = Field(..., description="Potential challenges in scraping this website")
    performance_tips: list[str] = Field(..., description="Tips for improving scraper performance")

    sample_parse_function: str = Field(..., description="Sample parse function structure")


class FileAction(ExtendedBaseModel):
    """Action to be taken on a file."""

    file: str = Field(description="The name of the file to create, overwrite, append to or delete")
    action_type: Literal["create", "overwrite", "delete", "append"] = Field(description="The type of action to take on the file")
    content: str = Field(None, description="The content for file creation, if creating, overwriting, or appending")


class GeneratorAction(ExtendedBaseModel):
    """Action to be taken by the generator agent."""

    actions: list[FileAction] = Field(description="List of file actions to perform")
    is_final: bool = Field(description="Whether the spider is completed")


class ActionExecutionFeedBack(BaseModel):
    """Feedback on the execution of an action."""

    success: bool = Field(description="Whether the action was successful", default=False)
    message: str = Field(description="A message describing the result of the action", default="")


class ActionMemory(BaseModel):
    """Memory of an action."""

    action: GeneratorAction = Field(description="The action that was taken")
    feedback: list[ActionExecutionFeedBack] = Field(description="Feedback son the execution of the action")


class TestResult(ExtendedBaseModel):
    """Result of spider test run with recommendations."""

    success: bool = Field(description="Whether the test was successful")
    items_scraped: int = Field(description="Number of items scraped")
    recommendations: str = Field(description="Recommendations for improving the spider")
    needs_more_info: bool = Field(description="Whether more information is needed")
    url_to_analyze: str = Field(description="URL to analyze for more information")
    analysis_instructions: str = Field(description="Instructions for analyzing the URL")
