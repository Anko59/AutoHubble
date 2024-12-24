import json

import undetected_chromedriver as uc
from loguru import logger


class ChromeDriver:
    def setup_chrome_options(self) -> uc.ChromeOptions:
        """Set up Chrome options for maximum stealth."""
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--headless=new")
        options.add_argument("--start-maximized")
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        # Custom user agent
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        options.add_argument(f"user-agent={user_agent}")

        # Experimental options
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": r"C:\temp",
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
            },
        )
        return options

    def __init__(self):
        """Initialize the ChromeDriver with stealth settings."""
        self.options = self.setup_chrome_options()
        self.driver = None

    def start(self):
        """Start the undetected ChromeDriver."""
        if self.driver is None or not self.driver.session_id:
            self.driver = uc.Chrome(options=self.options)
            self._inject_stealth_scripts()
        try:
            self.driver.current_url
        except Exception:
            self.driver = uc.Chrome(options=self.options)
            self._inject_stealth_scripts()
        return self.driver

    def quit(self):
        """Quit the driver if running."""
        if self.driver:
            self.driver.quit()

    def _inject_stealth_scripts(self):
        """Inject JavaScript to enhance stealth."""
        try:
            # Remove navigator.webdriver property
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        window.navigator.chrome = {
                            runtime: {}
                        };
                        const originalQuery = window.navigator.permissions.query;
                        window.navigator.permissions.query = (parameters) => (
                            parameters.name === 'notifications'
                                ? Promise.resolve({ state: 'denied' })
                                : originalQuery(parameters)
                        );
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3],
                        });
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en'],
                        });
                    """
                },
            )
        except Exception as e:
            logger.error(f"Error injecting stealth scripts: {str(e)}")

    def capture_network_requests(self, driver) -> list[dict]:
        """Capture and analyze network requests for potential API endpoints.

        Returns:
            list of relevant network requests
        """
        network_requests = []

        try:
            # Get Performance logs
            logs = driver.get_log("performance")

            for entry in logs:
                try:
                    log_data = json.loads(entry.get("message", "{}"))
                    message = log_data.get("message", {})

                    if "Network.response" in message.get("method", "") or "Network.request" in message.get("method", ""):
                        params = message.get("params", {})
                        request = params.get("request", {})
                        url = request.get("url")
                        method = request.get("method")
                        headers = request.get("headers", {})
                        response_type = params.get("response", {}).get("mimeType", "")

                        # Filter out non-essential resource types
                        if url and self.is_relevant_request(url, response_type):
                            network_requests.append(
                                {
                                    "url": url,
                                    "method": method,
                                    "type": "xhr" if "xmlhttprequest" in str(params).lower() else "regular",
                                    "headers": headers,
                                    "response_type": response_type,
                                }
                            )
                            logger.debug(f"Captured network request: {method} {url}")
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse log entry: {entry}")
                except Exception as e:
                    logger.warning(f"Error parsing network log entry: {str(e)}")
        except Exception as e:
            logger.error(f"Error capturing network requests: {str(e)}")

        return network_requests

    def is_relevant_request(self, url: str, response_type: str) -> bool:
        """Check if the request is relevant for scraping purposes."""
        if not url:
            return False

        irrelevant_extensions = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".woff", ".woff2", ".ttf", ".eot")
        irrelevant_mimetypes = ("image/", "text/css", "font/")

        if any(x in url.lower() for x in irrelevant_extensions):
            return False

        if response_type and any(mimetype in response_type.lower() for mimetype in irrelevant_mimetypes):
            return False

        return True
