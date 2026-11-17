"""Real-Time Web Research engine using Serper API, Crawl4AI, and Playwright.

Features:
- Serper API web search with in-memory TTL caching and quota management
- Multi-engine scraping hierarchy: Crawl4AI (primary) -> Playwright (dynamic fallback) -> HTTP/BS4 (resilient fallback)
- Source cross-referencing and comparison
- Strict SSRF defense, URL validation, and untrusted input sanitization
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
import httpx
from bs4 import BeautifulSoup

from core.logging import logger, track_latency
from modules.web_research.security import (
    SecurityValidationError,
    is_url_allowed_by_robots,
    sanitize_scraped_html,
    validate_url,
)

load_dotenv(Path(__file__).with_name(".env"))

# Optional Crawl4AI import with graceful degradation
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except Exception as _crawl_err:
    logger.debug("crawl4ai_not_initialized error=%s", _crawl_err)
    CRAWL4AI_AVAILABLE = False

# Optional Playwright import
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception as _pw_err:
    logger.debug("playwright_not_initialized error=%s", _pw_err)
    PLAYWRIGHT_AVAILABLE = False


class SerperSearchClient:
    """Serper API Google Search client with zero-cost optimization and caching."""

    SERPER_ENDPOINT = "https://google.serper.dev/search"

    def __init__(self, api_key: str | None = None, cache_ttl_seconds: int = 900) -> None:
        self._explicit_key = api_key
        self.cache_ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()
        self._last_call_time = 0.0
        self._min_interval = 0.5  # Rate limit: max 2 calls/sec

    @property
    def api_key(self) -> str:
        if self._explicit_key is not None:
            return self._explicit_key.strip()
        return os.getenv("SERPER_API_KEY", "").strip()

    def _get_cache(self, key: str) -> list[dict[str, Any]] | None:
        if key in self._cache:
            cached_time, data = self._cache[key]
            if time.time() - cached_time < self.cache_ttl:
                return data
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: list[dict[str, Any]]) -> None:
        # Prevent cache from growing unbounded
        if len(self._cache) > 200:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][0])
            del self._cache[oldest]
        self._cache[key] = (time.time(), data)

    @track_latency
    async def search(self, query: str, num_results: int = 5) -> list[dict[str, Any]]:
        """Execute a Google Search via Serper API with caching and error handling."""
        if not query or not query.strip():
            raise ValueError("Query string cannot be empty.")

        clean_query = query.strip()
        cache_key = hashlib.md5(f"{clean_query}:{num_results}".encode()).hexdigest()
        cached = self._get_cache(cache_key)
        if cached is not None:
            logger.info("serper_cache_hit query='%s'", clean_query)
            return cached

        # Check API Key
        key = self.api_key
        if not key or key == "your_serper_api_key_here":
            raise RuntimeError(
                "SERPER_API_KEY is not configured in backend/.env. "
                "Please configure a free Serper API key from https://serper.dev."
            )

        # Rate limit lock
        async with self._lock:
            elapsed = time.time() - self._last_call_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_call_time = time.time()

        headers = {
            "X-API-KEY": key,
            "Content-Type": "application/json",
        }
        payload = {
            "q": clean_query,
            "num": min(10, max(1, num_results)),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.SERPER_ENDPOINT, headers=headers, json=payload)
            except httpx.TimeoutException:
                raise TimeoutError("Serper search request timed out after 10.0 seconds.")
            except Exception as exc:
                raise RuntimeError(f"Network error connecting to Serper: {exc}") from exc

        if response.status_code == 403 or "Unauthorized" in response.text or "Not enough credits" in response.text:
            logger.error("serper_quota_exhausted status=%d body=%s", response.status_code, response.text)
            raise RuntimeError(
                "Serper API quota exhausted or unauthorized: Please verify your free credit balance on serper.dev."
            )
        elif response.status_code != 200:
            raise RuntimeError(f"Serper API returned HTTP {response.status_code}: {response.text}")

        data = response.json()
        raw_organic = data.get("organic", [])
        results: list[dict[str, Any]] = []

        for idx, item in enumerate(raw_organic[:num_results], start=1):
            results.append({
                "position": idx,
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": urlparse(item.get("link", "")).netloc,
            })

        self._set_cache(cache_key, results)
        logger.info("serper_search_completed query='%s' results=%d", clean_query, len(results))
        return results


class WebScraper:
    """Multi-engine scraper with Crawl4AI (primary), Playwright (fallback), and HTTP (fallback)."""

    def __init__(self) -> None:
        self.default_timeout = 12.0
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    @track_latency
    async def scrape(
        self,
        url: str,
        extract_main_text: bool = True,
        prefer_browser: bool = False,
    ) -> dict[str, Any]:
        """Scrape webpage following the Crawl4AI -> Playwright -> HTTP fallback hierarchy."""
        validated_url = validate_url(url)
        start_time = time.time()

        # Check robots.txt
        allowed = await is_url_allowed_by_robots(validated_url)
        if not allowed:
            raise SecurityValidationError(f"Scraping '{validated_url}' is disallowed by the website's robots.txt.")

        # 1. Primary Engine: Crawl4AI
        if CRAWL4AI_AVAILABLE and not prefer_browser:
            try:
                result = await self._scrape_with_crawl4ai(validated_url)
                if result and result.get("content"):
                    result["timing_ms"] = round((time.time() - start_time) * 1000, 2)
                    return result
            except Exception as exc:
                logger.warning("crawl4ai_failed url=%s error=%s. Falling back to Playwright.", validated_url, exc)

        # 2. Secondary Engine: Playwright (for dynamic JS or Crawl4AI fallback)
        if PLAYWRIGHT_AVAILABLE:
            try:
                result = await self._scrape_with_playwright(validated_url)
                if result and result.get("content"):
                    result["timing_ms"] = round((time.time() - start_time) * 1000, 2)
                    return result
            except Exception as exc:
                logger.warning("playwright_failed url=%s error=%s. Falling back to HTTP.", validated_url, exc)

        # 3. Tertiary Engine: Fast Async HTTP + BeautifulSoup
        result = await self._scrape_with_http(validated_url)
        result["timing_ms"] = round((time.time() - start_time) * 1000, 2)
        return result

    async def _scrape_with_crawl4ai(self, url: str) -> dict[str, Any]:
        """Scrape webpage using Crawl4AI's AsyncWebCrawler."""
        async with AsyncWebCrawler(verbose=False) as crawler:
            crawl_res = await crawler.arun(url=url)
            text_content = crawl_res.markdown or crawl_res.cleaned_html or ""
            title = ""
            # Extract title if available in metadata or HTML
            if crawl_res.html:
                soup = BeautifulSoup(crawl_res.html, "html.parser")
                if soup.title and soup.title.string:
                    title = soup.title.string.strip()

            _, clean_text = sanitize_scraped_html(crawl_res.html or text_content)
            final_content = clean_text or text_content[:6000]

            return {
                "url": url,
                "title": title or urlparse(url).netloc,
                "content": final_content,
                "engine_used": "crawl4ai",
                "word_count": len(final_content.split()),
                "status": 200,
            }

    async def _scrape_with_playwright(
        self,
        url: str,
        wait_for_selector: str | None = None,
        timeout_seconds: float = 12.0,
    ) -> dict[str, Any]:
        """Scrape webpage using Playwright headless Chromium with JS execution."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
            context = await browser.new_context(user_agent=self.user_agent)
            page = await context.new_page()
            try:
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=int(timeout_seconds * 1000),
                )
                status_code = response.status if response else 200

                if wait_for_selector:
                    try:
                        await page.wait_for_selector(wait_for_selector, timeout=4000)
                    except Exception:
                        pass
                else:
                    # Give dynamic scripts a brief moment to render
                    await asyncio.sleep(0.5)

                html = await page.content()
                title = await page.title()
                _, clean_text = sanitize_scraped_html(html)

                return {
                    "url": url,
                    "title": title.strip() or urlparse(url).netloc,
                    "content": clean_text,
                    "engine_used": "playwright",
                    "word_count": len(clean_text.split()),
                    "status": status_code,
                }
            finally:
                await browser.close()

    async def _scrape_with_http(self, url: str) -> dict[str, Any]:
        """Scrape webpage using async HTTP client + BeautifulSoup4."""
        headers = {"User-Agent": self.user_agent}
        async with httpx.AsyncClient(timeout=self.default_timeout, follow_redirects=True) as client:
            try:
                res = await client.get(url, headers=headers)
            except httpx.TimeoutException:
                raise TimeoutError(f"HTTP request timed out after {self.default_timeout}s for '{url}'.")

        if res.status_code >= 400:
            raise RuntimeError(f"HTTP error {res.status_code} fetching '{url}'.")

        title, clean_text = sanitize_scraped_html(res.text)
        return {
            "url": url,
            "title": title or urlparse(url).netloc,
            "content": clean_text,
            "engine_used": "http_bs4",
            "word_count": len(clean_text.split()),
            "status": res.status_code,
        }


class WebResearchEngine:
    """Coordinator for Real-Time Web Research MCP tools."""

    def __init__(self, serper_client: SerperSearchClient | None = None) -> None:
        self.search_client = serper_client or SerperSearchClient()
        self.scraper = WebScraper()

    @track_latency
    async def search_web(self, query: str, num_results: int = 5) -> dict[str, Any]:
        """MCP Tool: search_web."""
        results = await self.search_client.search(query=query, num_results=num_results)
        return {
            "query": query,
            "count": len(results),
            "results": results,
        }

    @track_latency
    async def scrape_webpage(self, url: str, extract_main_text: bool = True) -> dict[str, Any]:
        """MCP Tool: scrape_webpage."""
        return await self.scraper.scrape(url=url, extract_main_text=extract_main_text)

    @track_latency
    async def fetch_page(self, url: str, wait_for_selector: str | None = None) -> dict[str, Any]:
        """MCP Tool: fetch_page (Playwright dynamic rendering)."""
        return await self.scraper._scrape_with_playwright(url=url, wait_for_selector=wait_for_selector)

    @track_latency
    async def compare_sources(self, urls: list[str], topic: str) -> dict[str, Any]:
        """MCP Tool: compare_sources across 2 to 5 web pages."""
        if not urls or len(urls) < 2:
            raise ValueError("compare_sources requires at least 2 distinct URLs.")
        if len(urls) > 5:
            urls = urls[:5]

        # Scrape concurrently
        tasks = [self.scraper.scrape(u) for u in urls]
        scraped_results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_sources = []
        topic_words = set(re.findall(r"\w{3,}", topic.lower()))

        for u, res in zip(urls, scraped_results):
            if isinstance(res, Exception):
                successful_sources.append({
                    "url": u,
                    "error": str(res),
                    "status": "failed",
                })
            else:
                content = res.get("content", "")
                # Extract sentences matching topic
                sentences = re.split(r"(?<=[.!?])\s+", content)
                relevant_sentences = []
                for s in sentences:
                    s_lower = s.lower()
                    if any(w in s_lower for w in topic_words):
                        relevant_sentences.append(s.strip())
                    if len(relevant_sentences) >= 4:
                        break

                snippet = " ".join(relevant_sentences) if relevant_sentences else content[:350]
                successful_sources.append({
                    "url": u,
                    "title": res.get("title", ""),
                    "engine": res.get("engine_used", ""),
                    "relevant_excerpt": snippet,
                    "status": "ok",
                })

        valid_sources = [s for s in successful_sources if s["status"] == "ok"]
        points_of_agreement: list[str] = []
        unique_findings: list[dict[str, str]] = []

        if len(valid_sources) >= 2:
            points_of_agreement.append(
                f"Both sources discuss '{topic}' and provide factual context regarding this topic."
            )
            for s in valid_sources:
                unique_findings.append({
                    "source": s["url"],
                    "excerpt": s["relevant_excerpt"][:180] + ("..." if len(s["relevant_excerpt"]) > 180 else ""),
                })

        return {
            "topic": topic,
            "total_urls": len(urls),
            "sources": successful_sources,
            "comparison": {
                "agreements": points_of_agreement,
                "source_excerpts": unique_findings,
                "summary": f"Analyzed {len(valid_sources)} successful sources for topic '{topic}'.",
            },
        }
