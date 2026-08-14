"""
SQLite database layer. Do tables:
1. jobs   -> har search request ka tracking (status, progress)
2. leads  -> actual extracted lead data
"""
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    status TEXT DEFAULT 'pending',   -- pending, running, completed, failed
    total_urls INTEGER DEFAULT 0,
    processed_urls INTEGER DEFAULT 0,
    leads_found INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error TEXT
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    company_name TEXT,
    email TEXT,
    phone TEXT,
    website TEXT,
    address TEXT,
    source_url TEXT NOT NULL,
    score INTEGER DEFAULT 0,
    email_verified INTEGER DEFAULT 0,
    extraction_method TEXT,          -- 'regex' or 'llm_fallback'
    raw_text_snippet TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs (id)
);

CREATE INDEX IF NOT EXISTS idx_leads_job_id ON leads(job_id);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_website ON leads(website);
"""


@contextmanager
def get_db():
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)


# ---------- Job operations ----------

def create_job(job_id: str, query: str):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO jobs (id, query, status, created_at, updated_at) VALUES (?, ?, 'pending', ?, ?)",
            (job_id, query, now, now),
        )


def update_job(job_id: str, **fields):
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    with get_db() as conn:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)


def get_job(job_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_jobs(limit: int = 50):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Lead operations ----------

def insert_lead(job_id: str, lead: dict):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO leads
               (job_id, company_name, email, phone, website, address,
                source_url, score, email_verified, extraction_method,
                raw_text_snippet, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job_id,
                lead.get("company_name"),
                lead.get("email"),
                lead.get("phone"),
                lead.get("website"),
                lead.get("address"),
                lead.get("source_url"),
                lead.get("score", 0),
                int(lead.get("email_verified", False)),
                lead.get("extraction_method"),
                lead.get("raw_text_snippet", "")[:300],
                now,
            ),
        )


def email_exists(email: str) -> bool:
    if not email:
        return False
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM leads WHERE email = ? LIMIT 1", (email,)).fetchone()
        return row is not None


def domain_exists(website: str) -> bool:
    if not website:
        return False
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM leads WHERE website = ? LIMIT 1", (website,)).fetchone()
        return row is not None


def get_leads(job_id: str = None, min_score: int = 0, has_email: bool = None, page: int = 1, page_size: int = 50):
    query = "SELECT * FROM leads WHERE score >= ?"
    params = [min_score]
    if job_id:
        query += " AND job_id = ?"
        params.append(job_id)
    if has_email is True:
        query += " AND email IS NOT NULL AND email != ''"
    elif has_email is False:
        query += " AND (email IS NULL OR email = '')"
    query += " ORDER BY score DESC LIMIT ? OFFSET ?"
    params += [page_size, (page - 1) * page_size]
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def delete_lead(lead_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
