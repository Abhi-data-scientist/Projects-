"""
Export Agent: stored leads ko CSV, JSON, ya Excel format mein export karta hai.
"""
import json
import os
import pandas as pd
from app.config import settings
from app.database import get_leads

os.makedirs(settings.EXPORT_DIR, exist_ok=True)


def _fetch_leads_df(job_id: str = None, min_score: int = 0) -> pd.DataFrame:
    leads = get_leads(job_id=job_id, min_score=min_score, page=1, page_size=10000)
    if not leads:
        return pd.DataFrame(columns=[
            "id", "company_name", "email", "phone", "website",
            "address", "source_url", "score", "email_verified",
            "extraction_method", "created_at",
        ])
    df = pd.DataFrame(leads)
    # raw_text_snippet aur job_id export mein nahi chahiye - clutter hai
    drop_cols = [c for c in ("raw_text_snippet", "job_id") if c in df.columns]
    return df.drop(columns=drop_cols)


def export_csv(job_id: str, min_score: int = 0) -> str:
    df = _fetch_leads_df(job_id, min_score)
    path = os.path.join(settings.EXPORT_DIR, f"{job_id}.csv")
    df.to_csv(path, index=False)
    return path


def _clean_nan(value):
    """pandas NaN/NaT ko JSON-safe None mein convert karta hai."""
    if value is None:
        return None
    if isinstance(value, float) and value != value:  # NaN != NaN is True
        return None
    return value


def export_json(job_id: str, min_score: int = 0) -> str:
    df = _fetch_leads_df(job_id, min_score)
    path = os.path.join(settings.EXPORT_DIR, f"{job_id}.json")
    records = df.to_dict(orient="records")
    # Record-level cleanup - pandas dtype quirks se independent, reliable hai
    records = [{k: _clean_nan(v) for k, v in rec.items()} for rec in records]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    return path


def export_xlsx(job_id: str, min_score: int = 0) -> str:
    df = _fetch_leads_df(job_id, min_score)
    path = os.path.join(settings.EXPORT_DIR, f"{job_id}.xlsx")
    df.to_excel(path, index=False, engine="openpyxl")
    return path


EXPORTERS = {
    "csv": export_csv,
    "json": export_json,
    "xlsx": export_xlsx,
}


def export_leads(job_id: str, fmt: str = "csv", min_score: int = 0) -> str:
    if fmt not in EXPORTERS:
        raise ValueError(f"Unsupported format: {fmt}. Use one of {list(EXPORTERS)}")
    return EXPORTERS[fmt](job_id, min_score)
