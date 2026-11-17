"""Web Research domain module: Search engine, web scraper, SSRF security, and MCP tools."""
from modules.web_research.engine import WebResearchEngine
from modules.web_research.security import SecurityValidationError, validate_url, is_url_allowed_by_robots, sanitize_scraped_html
from modules.web_research.tools import WebResearchToolGroup

__all__ = [
    "WebResearchEngine",
    "SecurityValidationError",
    "validate_url",
    "is_url_allowed_by_robots",
    "sanitize_scraped_html",
    "WebResearchToolGroup",
]
