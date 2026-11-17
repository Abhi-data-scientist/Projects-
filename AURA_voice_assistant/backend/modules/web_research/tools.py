"""MCP Tool Group for Real-Time Web Research.

Implements Model Context Protocol (MCP) schemas and execution dispatchers for:
1. search_web
2. scrape_webpage
3. fetch_page
4. compare_sources
"""

from __future__ import annotations

import json
from typing import Any

from core.logging import logger, track_latency
from modules.web_research.engine import WebResearchEngine


class WebResearchToolGroup:
    """Model Context Protocol (MCP) tool group for Real-Time Web Research."""

    def __init__(self, engine: WebResearchEngine | None = None) -> None:
        self.engine = engine or WebResearchEngine()

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return MCP-compliant tool definitions with standard JSON Schemas."""
        return [
            {
                "name": "search_web",
                "description": (
                    "Search the web in real-time using Google Search (via Serper API). "
                    "Returns ranked organic search results with titles, source URLs, and snippet excerpts."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search term or current topic to query on Google.",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of search results to return (default: 5, max: 10).",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "scrape_webpage",
                "description": (
                    "Scrape and extract clean text or markdown from a specific URL using Crawl4AI "
                    "with Playwright and HTTP fallbacks. Enforces SSRF defense and robots.txt checks."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The public HTTP/HTTPS URL of the webpage to scrape.",
                        },
                        "extract_main_text": {
                            "type": "boolean",
                            "description": "Whether to extract clean text/markdown and strip boilerplate (default: true).",
                            "default": True,
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "fetch_page",
                "description": (
                    "Render and fetch dynamic, JavaScript-heavy webpages using Playwright headless Chromium. "
                    "Allows waiting for a specific CSS selector or network idle."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The target webpage URL to render with headless browser.",
                        },
                        "wait_for_selector": {
                            "type": "string",
                            "description": "Optional CSS selector to wait for before extracting page content.",
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "compare_sources",
                "description": (
                    "Concurrently scrape and cross-reference 2 to 5 web sources for a given topic. "
                    "Extracts points of agreement, differences, and synthesizes evidence."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of 2 to 5 public URLs to scrape and compare.",
                        },
                        "topic": {
                            "type": "string",
                            "description": "The specific subject or question to cross-reference across the sources.",
                        },
                    },
                    "required": ["urls", "topic"],
                },
            },
        ]

    def get_groq_tools(self) -> list[dict[str, Any]]:
        """Return OpenAI/Groq function calling format for the tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["inputSchema"],
                },
            }
            for t in self.get_tool_definitions()
        ]

    @track_latency
    async def execute_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """MCP standard tool execution dispatcher.

        Returns MCP-compliant response:
        {"content": [{"type": "text", "text": "..."}], "isError": bool}
        """
        args = arguments or {}
        try:
            if name == "search_web":
                query = args.get("query", "")
                num_results = int(args.get("num_results", 5))
                res = await self.engine.search_web(query=query, num_results=num_results)
                return {
                    "content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}],
                    "isError": False,
                }

            elif name == "scrape_webpage":
                url = args.get("url", "")
                extract_main = bool(args.get("extract_main_text", True))
                res = await self.engine.scrape_webpage(url=url, extract_main_text=extract_main)
                return {
                    "content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}],
                    "isError": False,
                }

            elif name == "fetch_page":
                url = args.get("url", "")
                selector = args.get("wait_for_selector")
                res = await self.engine.fetch_page(url=url, wait_for_selector=selector)
                return {
                    "content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}],
                    "isError": False,
                }

            elif name == "compare_sources":
                urls = args.get("urls", [])
                topic = args.get("topic", "")
                res = await self.engine.compare_sources(urls=urls, topic=topic)
                return {
                    "content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}],
                    "isError": False,
                }

            else:
                return {
                    "content": [{"type": "text", "text": f"Unknown tool: '{name}'"}],
                    "isError": True,
                }

        except Exception as exc:
            logger.exception("web_tool_execution_failed tool=%s", name)
            return {
                "content": [{"type": "text", "text": f"Error executing tool '{name}': {exc}"}],
                "isError": True,
            }
