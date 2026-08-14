"""
Crawler Agent: Playwright se URLs ko load/render karta hai.
Async + semaphore se parallel crawling (default 5 pages ek saath).
JS-heavy sites bhi handle ho jate hain (normal requests/bs4 se nahi hote).
"""
import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from app.config import settings

logger = logging.getLogger(__name__)

# Realistic user agent - bahut sites bot-like requests block kar deti hain
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


async def _fetch_page(browser, url: str, timeout_ms: int) -> dict:
    """Ek single page fetch karta hai, error-safe."""
    page = None
    try:
        page = await browser.new_page(user_agent=USER_AGENT)
        await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        # Thoda wait taaki JS-rendered content bhi aa jaye
        await page.wait_for_timeout(1000)
        html = await page.content()
        return {"url": url, "html": html, "success": True, "error": None}
    except PlaywrightTimeout:
        logger.warning(f"Timeout crawling: {url}")
        return {"url": url, "html": None, "success": False, "error": "timeout"}
    except Exception as e:
        logger.warning(f"Failed crawling {url}: {e}")
        return {"url": url, "html": None, "success": False, "error": str(e)}
    finally:
        if page:
            await page.close()


async def crawl_urls(
    urls: list[str],
    max_concurrent: int = None,
    timeout_ms: int = None,
    progress_callback=None,
) -> list[dict]:
    """
    URLs ki list leke parallel crawl karta hai.
    progress_callback(done_count, total_count) - agar SSE progress dikhana ho.
    """
    max_concurrent = max_concurrent or settings.MAX_CONCURRENT_CRAWLS
    timeout_ms = timeout_ms or settings.CRAWL_TIMEOUT_MS

    results = []
    sem = asyncio.Semaphore(max_concurrent)
    done_count = 0
    lock = asyncio.Lock()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        async def fetch_with_sem(url):
            nonlocal done_count
            async with sem:
                result = await _fetch_page(browser, url, timeout_ms)
                async with lock:
                    done_count += 1
                    if progress_callback:
                        progress_callback(done_count, len(urls))
                return result

        try:
            results = await asyncio.gather(*[fetch_with_sem(u) for u in urls])
        finally:
            await browser.close()

    success_count = sum(1 for r in results if r["success"])
    logger.info(f"Crawled {success_count}/{len(urls)} pages successfully")
    return results


def crawl_urls_sync(urls: list[str], **kwargs) -> list[dict]:
    """Sync wrapper - agar kahin non-async context se call karna ho."""
    return asyncio.run(crawl_urls(urls, **kwargs))
