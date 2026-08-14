"""
Discovery Agent: query leke DuckDuckGo se URLs fetch karta hai,
aur junk/social/PDF links ko filter kar deta hai.
"""
import time
import logging
from urllib.parse import urlparse
from ddgs import DDGS
from app.config import settings

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    """Junk domains aur file extensions skip karo."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
    except Exception:
        return False

    # Excluded domains check
    for bad_domain in settings.EXCLUDED_DOMAINS:
        if bad_domain in domain:
            return False

    # Excluded file extensions check
    path = parsed.path.lower()
    if path.endswith(settings.EXCLUDED_EXTENSIONS):
        return False

    # Must be http/https
    if parsed.scheme not in ("http", "https"):
        return False

    return True


def discover_urls(query: str, max_results: int = 20, extra_exclude: list[str] = None) -> list[str]:
    """
    DuckDuckGo se search karke valid URLs ki list deta hai.
    extra_exclude: user-specified additional domains to skip.
    """
    extra_exclude = extra_exclude or []
    raw_urls = []

    try:
        # naye ddgs package mein context manager (with) support nahi hai - direct call karo
        results = DDGS().text(query, max_results=max_results * 2)  # buffer for filtering
        for r in results:
            href = r.get("href")
            if href:
                raw_urls.append(href)
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return []

    # Filter
    filtered = []
    seen_domains = set()
    for url in raw_urls:
        if not is_valid_url(url):
            continue

        domain = urlparse(url).netloc.lower().replace("www.", "")
        if any(bad in domain for bad in extra_exclude):
            continue

        # Ek domain se sirf ek hi URL lo (avoid same-site duplicates)
        if domain in seen_domains:
            continue
        seen_domains.add(domain)

        filtered.append(url)
        if len(filtered) >= max_results:
            break

    logger.info(f"Discovery: {len(raw_urls)} raw -> {len(filtered)} filtered URLs for query '{query}'")
    return filtered


def discover_urls_bulk(queries: list[str], max_results_per_query: int = 20) -> dict[str, list[str]]:
    """
    Multiple queries ke liye discovery, rate-limit safe delay ke saath.
    """
    results = {}
    for q in queries:
        try:
            res = DDGS().text(q, max_results=max_results_per_query * 2)
            urls = [r["href"] for r in res if r.get("href")]
            results[q] = [u for u in urls if is_valid_url(u)][:max_results_per_query]
        except Exception as e:
            logger.error(f"Bulk discovery failed for '{q}': {e}")
            results[q] = []
        time.sleep(settings.DUCKDUCKGO_DELAY_SECONDS)
    return results