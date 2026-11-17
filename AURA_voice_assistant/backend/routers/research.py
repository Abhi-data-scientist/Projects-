"""Router for Real-Time Web Research, Google search, and scraping."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.logging import logger, track_latency
from modules.web_research import WebResearchEngine, SecurityValidationError

router = APIRouter(prefix="/api/research", tags=["research"])

web_research_engine = WebResearchEngine()


class WebSearchRequest(BaseModel):
    query: str
    num_results: int = 5


class WebScrapeRequest(BaseModel):
    url: str
    extract_main_text: bool = True


class WebFetchRequest(BaseModel):
    url: str
    wait_for_selector: str | None = None


class SourceCompareRequest(BaseModel):
    urls: list[str]
    topic: str


@router.post("/search")
@track_latency
async def search_endpoint(request: WebSearchRequest) -> dict:
    """Search Google in real-time via Serper API."""
    try:
        return await web_research_engine.search_web(
            query=request.query,
            num_results=request.num_results,
        )
    except Exception as exc:
        logger.exception("search_endpoint_failed query=%s", request.query)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/scrape")
@track_latency
async def scrape_endpoint(request: WebScrapeRequest) -> dict:
    """Scrape and sanitize webpage using Crawl4AI / Playwright / HTTP hierarchy."""
    try:
        return await web_research_engine.scrape_webpage(
            url=request.url,
            extract_main_text=request.extract_main_text,
        )
    except SecurityValidationError as sec_exc:
        raise HTTPException(status_code=400, detail=str(sec_exc)) from sec_exc
    except Exception as exc:
        logger.exception("scrape_endpoint_failed url=%s", request.url)
        raise HTTPException(
            status_code=400 if any(k in str(exc) for k in ["SSRF", "Blocked", "robots.txt"]) else 500,
            detail=str(exc),
        ) from exc


@router.post("/fetch")
@track_latency
async def fetch_endpoint(request: WebFetchRequest) -> dict:
    """Render dynamic JavaScript webpage using Playwright headless browser."""
    try:
        return await web_research_engine.fetch_page(
            url=request.url,
            wait_for_selector=request.wait_for_selector,
        )
    except Exception as exc:
        logger.exception("fetch_endpoint_failed url=%s", request.url)
        raise HTTPException(
            status_code=400 if any(k in str(exc) for k in ["SSRF", "Blocked"]) else 500,
            detail=str(exc),
        ) from exc


@router.post("/compare")
@track_latency
async def compare_endpoint(request: SourceCompareRequest) -> dict:
    """Scrape and cross-reference multiple web sources for a topic."""
    try:
        return await web_research_engine.compare_sources(
            urls=request.urls,
            topic=request.topic,
        )
    except Exception as exc:
        logger.exception("compare_endpoint_failed topic=%s", request.topic)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
