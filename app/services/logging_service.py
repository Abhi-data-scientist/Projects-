"""File-based audit logging. This service never writes logs to MySQL."""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("audit")


def log_event(event: str, **details):
    """Write one searchable JSON event to logs/app.log without logging secrets."""
    record = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **{key: value for key, value in details.items() if value is not None},
    }
    logger.info("%s", json.dumps(record, ensure_ascii=False, default=str))
