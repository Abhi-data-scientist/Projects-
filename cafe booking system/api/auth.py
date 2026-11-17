import logging
import re
from fastapi import APIRouter, Form, HTTPException, Request

from services import auth_service, logging_service

logger = logging.getLogger("auth_api")
router = APIRouter(prefix="/auth", tags=["auth"])


def _token_from_request(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.query_params.get("token", "")


@router.post("/register")
async def register(
    name: str | None = Form(default=None),
    phone: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        if not re.fullmatch(r"\+[1-9]\d{7,14}", phone.replace(" ", "")):
            raise ValueError("Enter a WhatsApp number in international format, e.g. +919876543210.")
        result = auth_service.register(name, phone, email, password)
        logging_service.log_event("user_registered", user_id=result["user"]["id"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Register error: %s", e)
        raise HTTPException(status_code=500, detail="Registration failed.")


@router.post("/login")
async def login(
    phone_or_email: str | None = Form(default=None),
    identifier: str | None = Form(default=None),
    password: str = Form(...),
):
    login_value = (phone_or_email or identifier or "").strip()
    if not login_value:
        raise HTTPException(status_code=422, detail="phone_or_email is required.")
    result = auth_service.login(login_value, password)
    if not result:
        logging_service.log_event("login_failed")
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    logging_service.log_event("user_logged_in", user_id=result["user"]["id"])
    return result


@router.post("/logout")
async def logout(request: Request, token: str | None = Form(default=None)):
    token = token or _token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")
    auth_service.logout(token)
    logging_service.log_event("user_logged_out")
    return {"status": "logged_out"}


@router.get("/me")
async def me(request: Request):
    token = _token_from_request(request)
    user = auth_service.get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return user


@router.get("/sessions")
async def sessions(request: Request):
    """List the authenticated user's saved login sessions safely."""
    token = _token_from_request(request)
    user = auth_service.get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return {"sessions": auth_service.get_user_sessions(user["id"])}
