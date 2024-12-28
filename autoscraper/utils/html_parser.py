import json

import chompjs
from bs4 import BeautifulSoup, Comment
from loguru import logger

base_relevant_tags = {
    "html",  # Root element
    "a",  # Links
    "abbr",  # Abbreviations
    "address",  # Contact information
    "article",  # Content blocks
    "aside",  # Additional content
    "b",  # Bold text (may indicate importance)
    "blockquote",  # Quoted text
    "body",  # Main document content
    "button",  # Clickable buttons
    "caption",  # Table captions
    "cite",  # Titles of works
    "code",  # Code snippets
    "data",  # Machine-readable content
    "datalist",  # Predefined options for inputs
    "dd",  # Descriptions in lists
    "details",  # Expandable sections
    "div",  # Generic container
    "dl",  # Description lists
    "dt",  # Terms in description lists
    "em",  # Emphasized text
    "figcaption",  # Captions for figures
    "figure",  # Self-contained content
    "footer",  # Footer sections
    "form",  # Forms for user input
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",  # Headings
    "header",  # Header sections
    "img",  # Images
    "input",  # Form input fields
    "label",  # Labels for inputs
    "li",  # List items
    "main",  # Main content of the page
    "nav",  # Navigation links
    "ol",  # Ordered lists
    "option",  # Options in select inputs
    "p",  # Paragraphs
    "pre",  # Preformatted text
    "section",  # Page sections
    "select",  # Dropdowns
    "span",  # Inline content
    "strong",  # Important text
    "summary",  # Summaries for <details>
    "table",  # Data tables
    "tbody",  # Table body
    "td",  # Table cells
    "tfoot",  # Table footer
    "th",  # Table headers
    "thead",  # Table headers
    "title",  # Document title
    "tr",  # Table rows
    "ul",  # Unordered lists
}

base_attribute_whitelist = {
    "accept",
    "action",
    "alt",
    "class",
    "content",
    "data-*",  # For custom data attributes
    "href",
    "id",
    "name",
    "placeholder",
    "src",
    "title",
    "type",
    "value",
    # Less relevant attributes for scraping:
    # "accept-charset",
    # "autocomplete",
    # "autofocus",
    # "charset",
    # "cite",
    # "contenteditable",
    # "coords",
    # "datetime",
    # "dir",
    # "download",
    # "draggable",
    # "enctype",
    # "for",
    # "form",
    # "hreflang",
    # "inputmode",
    # "ismap",
    # "label",
    # "lang",
    # "list",
    # "max",
    # "maxlength",
    # "media",
    # "method",
    # "min",
    # "pattern",
    # "poster",
    # "preload",
    # "readonly",
    # "rel",
    # "required",
    # "role",
    # "rows",
    # "scope",
    # "selected",
    # "shape",
    # "size",
    # "spellcheck",
    # "srcset",
    # "step",
    # "style",
    # "tabindex",
    # "target",
    # "usemap",
    # "width",
}


MAX_JSON_LENGHT = 10000


class HTMLParser:
    """
    A configurable HTML parser for simplifying content while retaining essential information.
    Features:
    - Removes unnecessary tags, attributes, and comments.
    - Extracts JSON objects from <script> tags.
    - Collapses empty tags and retains only relevant HTML elements.
    """

    def __init__(
        self,
        relevant_tags: set[str] | None = None,
        attribute_whitelist: set[str] | None = None,
    ):
        """
        Initialize the HTMLParser with configurable options.

        :param relevant_tags: Set of HTML tags to retain (default: commonly used tags for scraping).
        :param attribute_whitelist: Set of attributes to retain in the tags (default: essential attributes for scraping).
        """
        self.relevant_tags: set[str] = relevant_tags or base_relevant_tags
        self.attribute_whitelist: set[str] = attribute_whitelist or base_attribute_whitelist

    def _remove_irrelevant_tags(self, soup: BeautifulSoup) -> None:
        """
        Remove tags not in the relevant tags list.
        """
        for tag in soup.find_all(True):  # True matches all tags
            if tag.name not in self.relevant_tags:
                tag.extract()

    def _remove_unnecessary_attributes(self, soup: BeautifulSoup) -> None:
        """
        Remove attributes not in the whitelist from all tags.
        """
        for tag in soup.find_all(True):
            attrs = {k: v for k, v in tag.attrs.items() if k in self.attribute_whitelist}
            tag.attrs = attrs

    def _extract_json_from_scripts(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        """
        Extract JSON objects from <script> tags and remove the <script> tags.
        """
        json_data: list[dict[str, str]] = []
        for script_index, script in enumerate(soup.find_all("script")):
            script_content = script.string
            if script_content:
                try:
                    extracted_data = chompjs.parse_js_object(script_content)
                    extracted_data = json.dumps(extracted_data)
                    if len(extracted_data) > MAX_JSON_LENGHT:
                        extracted_data = (
                            extracted_data[: int(MAX_JSON_LENGHT / 2)] + "...TRUNCATED..." + extracted_data[int(-MAX_JSON_LENGHT / 2) :]
                        )
                    json_data.append({"script_index": str(script_index), "data": extracted_data})
                except Exception as e:
                    logger.debug(f"Failed to extract JSON from script: {str(e)[0:100]}")
            script.extract()  # Remove all <script> tags
        return json_data

    def _remove_comments(self, soup: BeautifulSoup) -> None:
        """
        Remove comments from the HTML.
        """
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

    def _collapse_empty_tags(self, soup: BeautifulSoup) -> None:
        """
        Remove tags that are empty and have no attributes.
        """
        for tag in soup.find_all(True):
            if not tag.text.strip() and not tag.attrs:
                tag.extract()

    def parse(self, html: str) -> tuple[str, list[dict[str, str]]]:
        """
        Parse the input HTML and return the simplified HTML and extracted JSON data.

        :param html: Raw HTML content as a string.
        :return: Tuple of (simplified HTML, extracted JSON data).
        """
        soup = BeautifulSoup(html, "html.parser")
        logger.debug(f"Base html length: {len(str(soup))}")
        json_data = self._extract_json_from_scripts(soup)
        logger.debug(f"JSON data length: {len(json_data)}")
        logger.debug(f"After extracting JSON from scripts: {len(str(soup))}")
        # Perform all preprocessing steps
        self._remove_irrelevant_tags(soup)
        logger.debug(f"After removing irrelevant tags: {len(str(soup))}")
        self._remove_unnecessary_attributes(soup)
        logger.debug(f"After removing unnecessary attributes: {len(str(soup))}")
        self._remove_comments(soup)
        logger.debug(f"After removing comments: {len(str(soup))}")
        self._collapse_empty_tags(soup)
        logger.debug(f"After collapsing empty tags: {len(str(soup))}")

        # Return the cleaned HTML and extracted JSON
        return soup.prettify(), json_data
