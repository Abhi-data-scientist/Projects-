"""Web Security and SSRF validation module.

Validates URLs, blocks private/internal IPs, localhost, cloud metadata,
enforces protocol safety, checks robots.txt, and sanitizes untrusted HTML.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import httpx
from bs4 import BeautifulSoup

from core.logging import logger

# Blocked private and cloud metadata CIDR ranges (IPv4 and IPv6)
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local / Cloud metadata (AWS, GCP, Azure 169.254.169.254)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "instance-data",
}

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {80, 443, 8080, 8443}

# Cache robots.txt parsers per domain to reduce network requests
_robots_cache: dict[str, tuple[float, RobotFileParser | None]] = {}


class SecurityValidationError(ValueError):
    """Raised when a URL violates SSRF, protocol, or safety rules."""
    pass


def validate_url(url: str) -> str:
    """Validate URL format, scheme, host, and port, blocking SSRF attempts.

    Returns the normalized URL if valid; raises SecurityValidationError otherwise.
    """
    if not url or not isinstance(url, str):
        raise SecurityValidationError("URL must be a non-empty string.")

    cleaned_url = url.strip()
    try:
        parsed = urlparse(cleaned_url)
    except Exception as exc:
        raise SecurityValidationError(f"Malformed URL: {exc}") from exc

    # 1. Scheme check
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise SecurityValidationError(
            f"Blocked scheme '{scheme}'. Only HTTP and HTTPS are permitted."
        )

    # 2. Host check
    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise SecurityValidationError("URL is missing a valid hostname.")

    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".localhost") or hostname.endswith(".internal"):
        raise SecurityValidationError(f"Access to private hostname '{hostname}' is blocked.")

    # 3. Port check
    port = parsed.port
    if port and port not in ALLOWED_PORTS:
        raise SecurityValidationError(f"Blocked port {port}: not in the allowed ports list.")

    # 4. Resolve IP and block private/link-local/loopback addresses (SSRF defense)
    try:
        # Check if hostname is already a direct IP literal
        try:
            ip_obj = ipaddress.ip_address(hostname)
            _check_ip_safety(ip_obj)
        except ValueError:
            # It's a domain name; resolve IP addresses via DNS
            addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                _check_ip_safety(ip_obj)
    except SecurityValidationError:
        raise
    except socket.gaierror as exc:
        raise SecurityValidationError(f"Failed to resolve hostname '{hostname}': {exc}") from exc
    except Exception as exc:
        raise SecurityValidationError(f"SSRF validation failed for '{hostname}': {exc}") from exc

    return cleaned_url


def _check_ip_safety(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    """Check if an IP address belongs to any blocked private/internal ranges."""
    if ip_obj.is_loopback:
        raise SecurityValidationError(f"Blocked loopback IP: {ip_obj}")
    if ip_obj.is_private:
        raise SecurityValidationError(f"Blocked private IP: {ip_obj}")
    if ip_obj.is_link_local:
        raise SecurityValidationError(f"Blocked link-local IP: {ip_obj}")
    if ip_obj.is_unspecified:
        raise SecurityValidationError(f"Blocked unspecified IP: {ip_obj}")

    for network in BLOCKED_IP_NETWORKS:
        if ip_obj in network:
            raise SecurityValidationError(f"Blocked internal network IP '{ip_obj}' in {network}")


async def is_url_allowed_by_robots(url: str, user_agent: str = "*", timeout: float = 3.0) -> bool:
    """Asynchronously fetch and evaluate robots.txt for a given URL.

    Fail-open gracefully if robots.txt is unavailable or times out.
    """
    try:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{origin}/robots.txt"

        rfp = RobotFileParser()
        rfp.set_url(robots_url)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            res = await client.get(robots_url)
            if res.status_code == 200:
                lines = res.text.splitlines()
                rfp.parse(lines)
                allowed = rfp.can_fetch(user_agent, url)
                return allowed
            elif res.status_code in {401, 403}:
                # Site explicitly forbids crawling of the entire domain
                return False
            else:
                # 404 or other: no restrictions
                return True
    except Exception as exc:
        logger.debug("robots_check_failed url=%s error=%s (permitting crawl)", url, exc)
        return True


def sanitize_scraped_html(
    html_content: str,
    max_length: int = 7000,
) -> tuple[str, str]:
    """Sanitize untrusted HTML and extract clean readable text.

    Returns:
        tuple[title, clean_text_or_markdown]
    """
    if not html_content:
        return "", ""

    soup = BeautifulSoup(html_content, "html.parser")

    # Extract title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Strip dangerous/irrelevant elements
    for tag in soup(["script", "style", "nav", "header", "footer", "iframe", "noscript", "svg", "form", "button"]):
        tag.decompose()

    # Extract text from main content if available
    main_node = soup.find("article") or soup.find("main") or soup.find("div", {"id": re.compile(r"content|main", re.I)}) or soup.body or soup

    # Clean whitespace and extract text paragraphs
    text = main_node.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Join and eliminate duplicate empty lines
    cleaned = "\n".join(lines)

    # Truncate to maximum safety limit to prevent memory/token explosion
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "\n...[Content truncated for length]"

    return title, cleaned
