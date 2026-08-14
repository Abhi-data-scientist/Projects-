"""
Scorer Agent: lead ko weighted score deta hai based on kitna complete
aur verified data mila hai. Dedupe check bhi yahin se hota hai (database.py ke through).
"""
import logging
from app.config import settings
from app.database import email_exists, domain_exists

logger = logging.getLogger(__name__)


def calculate_score(lead: dict) -> int:
    """
    Weighted scoring:
    - email mila: +3
    - phone mila: +2
    - company name mila: +2
    - email verified (DNS check pass): +3
    Max possible score: 10
    """
    score = 0
    if lead.get("email"):
        score += settings.SCORE_EMAIL
    if lead.get("phone"):
        score += settings.SCORE_PHONE
    if lead.get("company_name"):
        score += settings.SCORE_COMPANY_NAME
    if lead.get("email_verified"):
        score += settings.SCORE_VERIFIED_EMAIL
    return score


def is_duplicate(email: str = None, website: str = None) -> bool:
    """
    Database mein check karta hai ki ye lead pehle se store hai ya nahi.
    Email match OR same domain match = duplicate.
    """
    if email and email_exists(email):
        return True
    if website and domain_exists(website):
        return True
    return False


def process_lead(raw_lead: dict) -> dict | None:
    """
    Ek raw extracted lead leke:
    1. Dedupe check karta hai
    2. Score calculate karta hai
    Returns None agar duplicate hai (skip kar do), warna processed lead.
    """
    email = raw_lead.get("email")
    website = raw_lead.get("website")

    if is_duplicate(email=email, website=website):
        logger.info(f"Duplicate skipped: {email or website}")
        return None

    raw_lead["score"] = calculate_score(raw_lead)
    return raw_lead
