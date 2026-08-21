"""
Structured logging utility.
- Console + rotating file logger for normal debug/error logs (app.log)
- JSONL pipeline logger: har request ke har stage ka ek JSON line -> pipeline.jsonl
  (isse dekh sakte ho kis stage pe kitna time laga / kya fail hua, bina poora log file padhe)
"""
import json
import logging
import os
import time
import uuid
from logging.handlers import RotatingFileHandler

from config import LOG_DIR

# ---------- Normal app logger ----------
logger = logging.getLogger("auto_invoicing")
logger.setLevel(logging.INFO)

_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formatter)

_file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "app.log"), maxBytes=5_000_000, backupCount=3
)
_file_handler.setFormatter(_formatter)

if not logger.handlers:
    logger.addHandler(_console_handler)
    logger.addHandler(_file_handler)

# ---------- JSONL pipeline logger ----------
PIPELINE_LOG_FILE = os.path.join(LOG_DIR, "pipeline.jsonl")


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def log_stage(request_id: str, stage: str, status: str, detail: dict | None = None):
    """
    Ek pipeline stage ka structured log likhta hai JSONL file me.
    status: "started" | "success" | "failed"
    """
    entry = {
        "request_id": request_id,
        "stage": stage,
        "status": status,
        "timestamp": time.time(),
        "detail": detail or {},
    }
    with open(PIPELINE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    # console pe bhi chhota sa summary
    if status == "failed":
        logger.error(f"[{request_id}] {stage} FAILED: {detail}")
    else:
        logger.info(f"[{request_id}] {stage} -> {status}")
