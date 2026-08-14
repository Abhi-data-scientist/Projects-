"""
Extractor Agent: raw HTML se clean text nikalta hai (Trafilatura)
aur regex se email/phone/company-name extract karta hai.
LLM ki zaroorat nahi is step mein - isliye fast aur free hai.
"""
import html as html_lib
import json
import re
import logging
import trafilatura
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------- Regex patterns ----------

EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# Indian + international phone numbers (10 digit, with optional +91, spaces, dashes)
PHONE_PATTERN = re.compile(
    r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4,6}'
)

# Common junk/placeholder emails to filter out (example.com, sentry, wordpress etc.)
JUNK_EMAIL_DOMAINS = (
    "example.com", "sentry.io", "wixpress.com", "godaddy.com",
    "yoursite.com", "domain.com", "email.com", "wordpress.com",
)


def extract_emails(html: str) -> list[str]:
    """HTML se saare valid-looking emails nikalta hai, junk filter karke."""
    found = set(EMAIL_PATTERN.findall(html))
    valid = []
    for email in found:
        email = email.lower().strip()
        domain = email.split("@")[-1]
        if domain in JUNK_EMAIL_DOMAINS:
            continue
        # image filenames jaise "photo@2x.png" ko exclude karo
        if any(email.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg")):
            continue
        valid.append(email)
    return valid


def extract_phones(text: str) -> list[str]:
    """Clean text se phone numbers nikalta hai. Digit-count se filter karta hai."""
    candidates = PHONE_PATTERN.findall(text)
    valid = []
    for c in candidates:
        digits = re.sub(r'\D', '', c)
        # 10-14 digits realistic phone number range (India +91 se US tak)
        if 10 <= len(digits) <= 14:
            valid.append(c.strip())
    # Duplicates hatao, order preserve karte hue
    seen = set()
    result = []
    for p in valid:
        digits = re.sub(r'\D', '', p)
        if digits not in seen:
            seen.add(digits)
            result.append(p)
    return result


def _clean_company_name(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    value = html_lib.unescape(re.sub(r"\s+", " ", value)).strip()
    return value if value and len(value) <= 120 else None


def _meta_content(html: str, attribute: str, value: str) -> str | None:
    """Return a meta tag's content regardless of the attribute order."""
    for tag in re.findall(r'<meta\b[^>]*>', html, re.IGNORECASE):
        has_key = re.search(rf'\b{attribute}\s*=\s*["\']{re.escape(value)}["\']', tag, re.IGNORECASE)
        content = re.search(r'\bcontent\s*=\s*["\'](.*?)["\']', tag, re.IGNORECASE)
        if has_key and content:
            return _clean_company_name(content.group(1))
    return None


def _company_name_from_json_ld(html: str) -> str | None:
    """Read a business name from Organization/LocalBusiness JSON-LD."""
    scripts = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.I | re.S)
    organization_types = {"organization", "localbusiness", "corporation", "company", "business"}

    def find_name(item) -> str | None:
        if isinstance(item, list):
            for child in item:
                if name := find_name(child):
                    return name
        elif isinstance(item, dict):
            item_types = item.get("@type", [])
            if isinstance(item_types, str):
                item_types = [item_types]
            if any(str(kind).lower() in organization_types for kind in item_types):
                return _clean_company_name(item.get("legalName") or item.get("name"))
            for child in item.values():
                if name := find_name(child):
                    return name
        return None

    for script in scripts:
        try:
            if name := find_name(json.loads(html_lib.unescape(script).strip())):
                return name
        except json.JSONDecodeError:
            continue
    return None


def extract_company_name(html: str, url: str) -> str:
    """
    Company name metadata/JSON-LD se nikalne ki koshish, phir domain name fallback.
    """
    reliable_name = (
        _meta_content(html, "property", "og:site_name")
        or _meta_content(html, "name", "application-name")
        or _company_name_from_json_ld(html)
    )
    if reliable_name:
        return reliable_name

    # A document title is frequently a page headline or a person's job title.
    # Use a transparent domain fallback instead of saving it as a company name.
    # Do not infer a company from <title>; it is often a role or page headline.
    title_match = None
    if title_match:
        title = title_match.group(1).strip()
        # Common suffixes hatao jaise "| Home", "- Official Site"
        title = re.split(r'[\|\-–—]', title)[0].strip()
        if title and len(title) < 100:
            return title

    # Fallback: domain name se guess karo
    domain = urlparse(url).netloc.replace("www.", "")
    name = domain.split(".")[0]
    return name.replace("-", " ").title()


def extract_data(html: str, url: str) -> dict:
    """
    Main extraction function - ek page ke liye poora structured data deta hai.
    """
    if not html:
        return {
            "url": url, "text": "", "emails": [], "phones": [],
            "company_name": None, "extraction_success": False,
        }

    clean_text = trafilatura.extract(html) or ""
    emails = extract_emails(html)
    phones = extract_phones(clean_text or html)
    company_name = extract_company_name(html, url)

    extraction_success = bool(emails or phones)

    return {
        "url": url,
        "text": clean_text,
        "emails": emails,
        "phones": phones,
        "company_name": company_name,
        "extraction_success": extraction_success,
    }


def needs_llm_fallback(extracted: dict) -> bool:
    """
    Decide karta hai ki is page ke liye Groq LLM fallback chahiye ya nahi.
    Sirf tab True jab regex se kuch nahi mila but text content hai.
    """
    has_contact = bool(extracted["emails"] or extracted["phones"])
    has_content = len(extracted.get("text", "") or "") > 100
    return (not has_contact) and has_content
