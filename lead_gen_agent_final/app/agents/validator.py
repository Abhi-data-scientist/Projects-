"""
Validator Agent: email format + deliverability check karta hai.
check_deliverability=True se DNS/MX record bhi verify hota hai (real domain hai ya nahi).
"""
import logging
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)


def is_valid_email(email: str, check_dns: bool = True) -> tuple[bool, str]:
    """
    Returns (is_valid, normalized_email_or_error_reason)
    check_dns=True: MX record verify karta hai (slower but accurate)
    check_dns=False: sirf format check (fast, offline)
    """
    if not email:
        return False, "empty"
    try:
        result = validate_email(email, check_deliverability=check_dns)
        return True, result.normalized
    except EmailNotValidError as e:
        return False, str(e)


def validate_lead_email(email: str, check_dns: bool = True) -> dict:
    """Lead ke liye validation result structured format mein."""
    if not email:
        return {"email": None, "is_valid": False, "verified": False}

    is_valid, result = is_valid_email(email, check_dns=check_dns)
    return {
        "email": result if is_valid else email,
        "is_valid": is_valid,
        "verified": is_valid and check_dns,
    }
