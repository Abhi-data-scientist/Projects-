"""
Validation & Calculation Engine.
- Required fields check karta hai
- Totals/tax hamesha yahan RECALCULATE hote hain (Gemini ke numbers pe trust nahi karte)
- Duplicate check ke liye ek stable hash banata hai
"""
import hashlib
import re
from datetime import datetime

from config import DEFAULT_TAX_RATE


class ValidationError(Exception):
    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__(", ".join(issues))


def normalize_date(value: str | None) -> str | None:
    """Convert common invoice date formats to MySQL's YYYY-MM-DD format."""
    if value is None or not str(value).strip():
        return None

    raw_date = re.sub(r"\s+", " ", str(value).strip().replace(",", ""))
    # Python accepts "Sep", while invoices frequently use the "Sept" spelling.
    raw_date = re.sub(r"\bSept\b", "Sep", raw_date, flags=re.IGNORECASE)
    for date_format in (
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
        "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y",
    ):
        try:
            return datetime.strptime(raw_date, date_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")


def validate_required_fields(data: dict) -> list[str]:
    """Missing critical fields ki list return karta hai (empty = sab theek)."""
    issues = []

    if not data.get("customer_name"):
        issues.append("customer_name missing")

    items = data.get("items") or []
    if not items:
        issues.append("no line items found")
    else:
        for i, item in enumerate(items):
            if not item.get("description"):
                issues.append(f"item[{i}].description missing")
            if item.get("quantity") in (None, "", 0):
                issues.append(f"item[{i}].quantity missing/zero")
            if item.get("unit_price") in (None, ""):
                issues.append(f"item[{i}].unit_price missing")

    return issues


def calculate_totals(items: list[dict], tax_rate_percent: float | None) -> dict:
    """
    Line-item totals, subtotal, tax, grand total -- sab yahan Python se calculate hote hain.
    """
    tax_rate = tax_rate_percent if tax_rate_percent is not None else DEFAULT_TAX_RATE

    line_items = []
    subtotal = 0.0

    for item in items:
        qty = float(item.get("quantity") or 0)
        unit_price = float(item.get("unit_price") or 0)
        line_total = round(qty * unit_price, 2)
        subtotal += line_total
        line_items.append(
            {
                "description": item.get("description", ""),
                "quantity": qty,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )

    subtotal = round(subtotal, 2)
    tax_amount = round(subtotal * (tax_rate / 100), 2)
    total_amount = round(subtotal + tax_amount, 2)

    return {
        "line_items": line_items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
    }


def compute_duplicate_hash(customer_name: str, total_amount: float, order_reference: str | None) -> str:
    """
    Duplicate detection ke liye stable hash.
    Same customer + same amount + same order ref (ya blank) = likely duplicate.
    """
    raw = f"{(customer_name or '').strip().lower()}|{total_amount}|{(order_reference or '').strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
