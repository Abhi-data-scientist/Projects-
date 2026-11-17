import secrets
import logging
from datetime import datetime, timedelta

import bcrypt

from core.config import settings
from core.database import execute_insert, execute_query, execute_select
from services.redis_client import rjson_get, rjson_set, rget, rset, rdelete

logger = logging.getLogger("auth_service")

_PROFILE_TTL = 86400   # 24 h
_SESSION_TTL = settings.SESSION_TTL_SECONDS


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def generate_token() -> str:
    return secrets.token_hex(32)


def _cache_profile(user: dict):
    uid = user["id"]
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    rjson_set(f"user:{uid}:profile", safe, _PROFILE_TTL)


def _load_user(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "phone": row["phone"],
        "email": row.get("email", ""),
        "created_at": str(row.get("created_at", "")),
    }


def register(name: str | None, phone: str | None, email: str, password: str) -> dict:
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Please enter a valid email address.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    name = (name or email.split("@", 1)[0]).strip()
    phone = (phone or "").strip() or None
    # Check duplicate
    if phone:
        existing = execute_select(
            "SELECT id FROM users WHERE phone=%s OR email=%s LIMIT 1", (phone, email)
        )
    else:
        existing = execute_select("SELECT id FROM users WHERE email=%s LIMIT 1", (email,))
    if existing:
        raise ValueError("Phone or email already registered.")

    pw_hash = hash_password(password)
    uid = execute_insert(
        "INSERT INTO users (name, phone, email, password_hash) VALUES (%s,%s,%s,%s)",
        (name, phone, email, pw_hash),
    )
    user = {"id": uid, "name": name, "phone": phone or "", "email": email}
    token = _create_session(uid)
    _cache_profile(user)
    log_activity(uid, "register", f"name={name} email={email}")
    logger.info("User registered id=%s email=%s", uid, email)
    return {"token": token, "user": user}


def login(identifier: str, password: str) -> dict | None:
    rows = execute_select(
        "SELECT * FROM users WHERE phone=%s OR email=%s LIMIT 1",
        (identifier, identifier),
    )
    if not rows:
        log_activity(None, "login_fail", f"identifier={identifier} reason=not_found")
        logger.warning("Login failed — user not found: %s", identifier)
        return None

    row = rows[0]
    if not row.get("password_hash") or not check_password(password, row["password_hash"]):
        log_activity(row["id"], "login_fail", "reason=bad_password")
        logger.warning("Login failed — bad password for user id=%s", row["id"])
        return None

    user = _load_user(row)
    token = _create_session(row["id"])
    _cache_profile(user)
    log_activity(row["id"], "login", f"email={row.get('email','')}")
    logger.info("User logged in id=%s", row["id"])
    return {"token": token, "user": user}


def _create_session(user_id: int) -> str:
    token = generate_token()
    expires_at = datetime.now() + timedelta(seconds=_SESSION_TTL)
    execute_insert(
        "INSERT INTO user_sessions (user_id, token, expires_at) VALUES (%s,%s,%s)",
        (user_id, token, expires_at.strftime("%Y-%m-%d %H:%M:%S")),
    )
    rset(f"cafe:session:{token}", str(user_id), _SESSION_TTL)
    return token


def logout(token: str) -> bool:
    uid_str = rget(f"cafe:session:{token}")
    rdelete(f"cafe:session:{token}")
    execute_query(
        "UPDATE user_sessions SET is_active=0 WHERE token=%s", (token,)
    )
    if uid_str:
        log_activity(int(uid_str), "logout", "")
    return True


def get_user_from_token(token: str) -> dict | None:
    if not token:
        return None
    # 1. Redis session → user_id
    uid_str = rget(f"cafe:session:{token}")
    if uid_str:
        uid = int(uid_str)
        # 2. Redis profile cache
        profile = rjson_get(f"user:{uid}:profile")
        if profile:
            return profile
        # 3. MySQL fallback
        rows = execute_select("SELECT * FROM users WHERE id=%s LIMIT 1", (uid,))
        if rows:
            user = _load_user(rows[0])
            _cache_profile(user)
            return user

    # 4. MySQL session fallback (Redis may be empty after restart)
    rows = execute_select(
        "SELECT u.* FROM users u "
        "JOIN user_sessions s ON s.user_id = u.id "
        "WHERE s.token=%s AND s.is_active=1 AND s.expires_at > NOW() LIMIT 1",
        (token,),
    )
    if rows:
        user = _load_user(rows[0])
        uid = user["id"]
        # Rebuild Redis session cache
        rset(f"cafe:session:{token}", str(uid), _SESSION_TTL)
        _cache_profile(user)
        return user
    return None


def get_user_sessions(user_id: int) -> list[dict]:
    """Return a safe session list for one user without exposing bearer tokens."""
    rows = execute_select(
        "SELECT id, created_at, expires_at, is_active FROM user_sessions "
        "WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,),
    )
    sessions = []
    for row in rows:
        sessions.append({
            "session_id": row["id"],
            "created_at": str(row["created_at"]),
            "expires_at": str(row["expires_at"]),
            "is_active": bool(row["is_active"]),
        })
    return sessions


def log_activity(user_id, action: str, details: str = ""):
    try:
        execute_insert(
            "INSERT INTO activity_logs (user_id, action, details) VALUES (%s,%s,%s)",
            (user_id, action, details),
        )
    except Exception as e:
        logger.warning("activity_log failed: %s", e)
