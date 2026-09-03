
import re
import os
import uuid
import logging
from datetime import datetime, date as date_type, timedelta
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Request

from core.config import settings
from services import auth_service, booking_service, session_service, llm_chat_service
from services import whisper_service, tts_service, whatsapp_service
from services import logging_service
from pydantic import BaseModel

logger = logging.getLogger("chat_api")
router = APIRouter()

# Steps (no get_name / get_phone anymore)
STEP_MAIN      = "main"
STEP_MEMBERS   = "get_members"
STEP_DATE      = "get_date"
STEP_CHECKIN   = "get_checkin"
STEP_CHECKOUT  = "get_checkout"
STEP_SEAT      = "get_seat"
STEP_CANCEL    = "cancel_confirm"
STEP_CANCEL_ALL = "cancel_all_confirm"
STEP_DONE      = "done"

MONTH_MAP = {
    "january":"01","february":"02","march":"03","april":"04",
    "may":"05","june":"06","july":"07","august":"08",
    "september":"09","october":"10","november":"11","december":"12",
    "jan":"01","feb":"02","mar":"03","apr":"04","jun":"06","jul":"07",
    "aug":"08","sep":"09","oct":"10","nov":"11","dec":"12",
}


class ChatResponse(BaseModel):
    reply: str
    step: str
    audio_url: str = ""
    transcribed: str = ""
    seats: list[dict] | None = None
    booking: dict | None = None


# ── Parsing helpers ────────────────────────────────────────────────────────────

def _parse_date(text: str) -> str | None:
    t = text.strip().lower()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d %m %Y"):
        try:
            return datetime.strptime(t, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Natural: "5 september 2026", "september 5", "5th sep"
    t2 = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", t)
    parts = t2.split()
    day = mon = year = None
    for p in parts:
        if p.isdigit():
            v = int(p)
            if 1 <= v <= 31 and day is None:
                day = v
            elif v > 31:
                year = v
        elif p in MONTH_MAP:
            mon = int(MONTH_MAP[p])
    if day and mon:
        if not year:
            year = date_type.today().year
            if date_type(year, mon, day) < date_type.today():
                year += 1
        try:
            return date_type(year, mon, day).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _parse_time(text: str) -> str | None:
    t = text.strip().lower().replace(".", ":").replace(" ", "")
    # "6pm" "6:30pm" "14:00" "6:00"
    m = re.match(r"(\d{1,2})(?::(\d{2}))?([ap]m)?$", t)
    if m:
        h, mn, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if ampm == "pm" and h != 12:
            h += 12
        elif ampm == "am" and h == 12:
            h = 0
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"
    return None


def _tts(text: str) -> str:
    try:
        path = tts_service.synthesize_speech(text)
        if path:
            return f"/audio/{Path(path).name}"
    except Exception as e:
        logger.warning("TTS failed: %s", e)
    return ""


def _reply(reply: str, step: str, seats=None, booking=None, transcribed="") -> ChatResponse:
    audio_url = _tts(reply) if settings.ENABLE_TTS else ""
    return ChatResponse(reply=reply, step=step, audio_url=audio_url,
                        transcribed=transcribed, seats=seats, booking=booking)


# ── Intent detection (keyword-based, no LLM) ──────────────────────────────────

def _detect_intent(msg: str) -> str:
    m = msg.lower()
    # Accept common spoken/typed variants such as "canncel" and "cancle".
    if re.search(r"\bcan+c(?:e|a)?l+\w*\b", m):
        return "cancel"
    if re.search(r"my.?booking|show.?booking|booking.?history|upcoming|previous.?booking", m):
        return "my_bookings"
    if re.search(r"\bbook\w*|\bseat\w*|\btable\w*|\breserv\w*", m):
        return "book"
    return "free"


def _wants_cancel_all(message: str) -> bool:
    return bool(re.search(r"\b(?:all|every)\b.*\bbook", message.lower()))


def _cancel_all_prompt(count: int) -> str:
    return (
        f"You have {count} active bookings. This will cancel all of them. "
        "Reply exactly 'YES CANCEL ALL' to confirm, or 'NO' to keep them."
    )


def _extract_booking_details(message: str) -> dict:
    """Extract common booking details from a natural-language message."""
    text = message.lower()
    details = {}

    members = re.search(
        r"\b(?:we\s+are|we're|for)?\s*(\d{1,2})\s*"
        r"(?:people|persons?|members?|guests?)\b",
        text,
    )
    if members:
        details["members"] = int(members.group(1))
    elif re.fullmatch(r"\s*\d{1,2}\s*", text):
        details["members"] = int(text.strip())

    month_names = "january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec"
    date_patterns = (
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{month_names})(?:\s+\d{{2,4}})?\b",
        rf"\b(?:{month_names})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{2,4}})?\b",
    )
    for pattern in date_patterns:
        found = re.search(pattern, text)
        if found:
            parsed_date = _parse_date(found.group(0).replace(",", ""))
            if parsed_date:
                details["date"] = parsed_date
                break

    time_matches = re.findall(
        r"\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\b|\b(?:[01]?\d|2[0-3]):[0-5]\d\b",
        text,
    )
    parsed_times = [_parse_time(t.replace(".", "").replace(" ", "")) for t in time_matches]
    parsed_times = [t for t in parsed_times if t]
    if parsed_times:
        details["checkin"] = parsed_times[0]
    if len(parsed_times) > 1:
        details["checkout"] = parsed_times[1]
    return details


def _continue_booking(ctx: dict, message: str) -> tuple[str, str, list[dict] | None]:
    """Merge supplied details and ask only for the next missing booking field."""
    details = _extract_booking_details(message)
    if "members" in details:
        if not 1 <= details["members"] <= 12:
            return "We can seat 1 to 12 members. How many will be joining?", STEP_MEMBERS, None
        ctx["members"] = details["members"]
    if "date" in details:
        if details["date"] < date_type.today().isoformat():
            return "That date has already passed. Please choose a future date.", STEP_DATE, None
        ctx["date"] = details["date"]
    if "checkin" in details:
        ctx["checkin"] = details["checkin"]
    if "checkout" in details:
        ctx["checkout"] = details["checkout"]

    if "members" not in ctx:
        ctx["step"] = STEP_MEMBERS
        return llm_chat_service.ask_members(), STEP_MEMBERS, None
    if "date" not in ctx:
        ctx["step"] = STEP_DATE
        return llm_chat_service.ask_date(), STEP_DATE, None
    if "checkin" not in ctx:
        ctx["step"] = STEP_CHECKIN
        return llm_chat_service.ask_checkin(), STEP_CHECKIN, None
    if "checkout" not in ctx:
        ctx["step"] = STEP_CHECKOUT
        return llm_chat_service.ask_checkout(), STEP_CHECKOUT, None
    if ctx["checkout"] <= ctx["checkin"]:
        ctx.pop("checkout", None)
        ctx["step"] = STEP_CHECKOUT
        return "Check-out must be after check-in. Please try again.", STEP_CHECKOUT, None

    checkin_dt = f"{ctx['date']} {ctx['checkin']}:00"
    checkout_dt = f"{ctx['date']} {ctx['checkout']}:00"
    seats = booking_service.get_available_seats(ctx["date"], checkin_dt, checkout_dt, ctx["members"])
    if not seats:
        ctx.clear()
        return llm_chat_service.no_seats_available(), STEP_MAIN, None
    ctx.update({
        "step": STEP_SEAT,
        "checkin_dt": checkin_dt,
        "checkout_dt": checkout_dt,
        "available_seat_ids": [s["id"] for s in seats],
    })
    return llm_chat_service.ask_seat_selection(len(seats)), STEP_SEAT, seats


# ── Main chat endpoint ────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(
    background_tasks: BackgroundTasks,
    request: Request,
    token: str | None = Form(default=None),
    message: str | None = Form(default=None),
    audio: UploadFile | None = File(default=None),
):
    # ── Auth ──────────────────────────────────────────────────────────────────
    auth_header = request.headers.get("Authorization", "")
    token = token or (auth_header[7:] if auth_header.startswith("Bearer ") else "")
    user = auth_service.get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    session_service.set_chat_session_id(token)
    uid = user["id"]
    name = user["name"]
    transcribed = ""
    logging_service.log_event("chat_request_started", user_id=uid, has_audio=audio is not None)

    # ── Voice → text ──────────────────────────────────────────────────────────
    if audio is not None:
        safe = Path(audio.filename or "upload").name
        tmp = os.path.join(settings.AUDIO_DIR, f"upload_{uuid.uuid4().hex}_{safe}")
        try:
            with open(tmp, "wb") as f:
                f.write(await audio.read())
            transcribed = whisper_service.transcribe_audio(tmp)
            message = transcribed
            logger.info("Transcribed uid=%s: %s", uid, transcribed)
            logging_service.log_event("voice_transcribed", user_id=uid, text_length=len(transcribed))
        except Exception as e:
            logger.error("Transcription failed: %s", e)
            logging_service.log_event("voice_transcription_failed", user_id=uid)
            return _reply("Sorry, I could not understand that audio. Please try again.", "error")
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    msg = (message or "").strip()
    ctx = session_service.get_booking_context(uid)
    step = ctx.get("step", STEP_MAIN)

    # ── First message — greet ─────────────────────────────────────────────────
    if not msg:
        history = session_service.get_chat_history(uid, limit=1)
        past_bookings = booking_service.get_bookings_by_user(uid)
        if history:
            reply = llm_chat_service.welcome_back(name, len(past_bookings))
        else:
            reply = llm_chat_service.new_user_welcome(name)
        session_service.append_chat_message(uid, "assistant", reply)
        return _reply(reply, STEP_MAIN, transcribed=transcribed)

    # Save user message
    session_service.append_chat_message(uid, "user", msg)

    # Booking actions must be interruptible. A user can ask for their bookings
    # or cancel one while an unfinished reservation is in progress.
    interrupt_intent = _detect_intent(msg)
    if step in {STEP_MEMBERS, STEP_DATE, STEP_CHECKIN, STEP_CHECKOUT, STEP_SEAT} and interrupt_intent in {"cancel", "my_bookings"}:
        session_service.clear_booking_context(uid)
        ctx = {}
        step = STEP_MAIN

    if step in {STEP_MEMBERS, STEP_DATE, STEP_CHECKIN, STEP_CHECKOUT}:
        r, next_step, seats = _continue_booking(ctx, msg)
        if next_step == STEP_MAIN:
            session_service.clear_booking_context(uid)
        else:
            session_service.set_booking_context(uid, ctx)
        session_service.append_chat_message(uid, "assistant", r)
        return _reply(r, next_step, seats=seats, transcribed=transcribed)

    # ── Booking flow steps ────────────────────────────────────────────────────

    if step == STEP_MEMBERS:
        nums = re.findall(r"\d+", msg)
        if not nums:
            r = llm_chat_service.ask_members()
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, step, transcribed=transcribed)
        members = int(nums[0])
        if members < 1 or members > 12:
            r = "We can seat 1 to 12 members. How many will be joining?"
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, step, transcribed=transcribed)
        ctx["members"] = members
        ctx["step"] = STEP_DATE
        session_service.set_booking_context(uid, ctx)
        r = llm_chat_service.ask_date()
        session_service.append_chat_message(uid, "assistant", r)
        return _reply(r, STEP_DATE, transcribed=transcribed)

    if step == STEP_DATE:
        parsed = _parse_date(msg)
        if not parsed:
            r = llm_chat_service.invalid_date()
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, step, transcribed=transcribed)
        if parsed < date_type.today().isoformat():
            r = "That date has already passed. Please choose a future date."
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, step, transcribed=transcribed)
        ctx["date"] = parsed
        ctx["step"] = STEP_CHECKIN
        session_service.set_booking_context(uid, ctx)
        r = llm_chat_service.ask_checkin()
        session_service.append_chat_message(uid, "assistant", r)
        return _reply(r, STEP_CHECKIN, transcribed=transcribed)

    if step == STEP_CHECKIN:
        parsed = _parse_time(msg)
        if not parsed:
            r = llm_chat_service.invalid_time()
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, step, transcribed=transcribed)
        ctx["checkin"] = parsed
        ctx["step"] = STEP_CHECKOUT
        session_service.set_booking_context(uid, ctx)
        r = llm_chat_service.ask_checkout()
        session_service.append_chat_message(uid, "assistant", r)
        return _reply(r, STEP_CHECKOUT, transcribed=transcribed)

    if step == STEP_CHECKOUT:
        parsed = _parse_time(msg)
        if not parsed:
            r = llm_chat_service.invalid_time()
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, step, transcribed=transcribed)
        if parsed <= ctx.get("checkin", "00:00"):
            r = "Check-out must be after check-in. Please try again."
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, step, transcribed=transcribed)
        ctx["checkout"] = parsed
        d = ctx["date"]
        ci = f"{d} {ctx['checkin']}:00"
        co = f"{d} {parsed}:00"
        seats = booking_service.get_available_seats(d, ci, co, ctx.get("members", 1))
        if not seats:
            r = llm_chat_service.no_seats_available()
            ctx["step"] = STEP_MAIN
            session_service.set_booking_context(uid, ctx)
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, STEP_MAIN, transcribed=transcribed)
        ctx["step"] = STEP_SEAT
        ctx["checkin_dt"] = ci
        ctx["checkout_dt"] = co
        ctx["available_seat_ids"] = [s["id"] for s in seats]
        session_service.set_booking_context(uid, ctx)
        r = llm_chat_service.ask_seat_selection(len(seats))
        session_service.append_chat_message(uid, "assistant", r)
        return _reply(r, STEP_SEAT, seats=seats, transcribed=transcribed)

    if step == STEP_SEAT:
        seat_num = msg.upper().strip()
        seat = booking_service.get_seat_by_number(seat_num)
        avail_ids = ctx.get("available_seat_ids", [])
        if not seat or seat["id"] not in avail_ids:
            r = llm_chat_service.seat_not_available(seat_num)
            seats = [booking_service.get_seat_by_id(i) for i in avail_ids]
            seats = [s for s in seats if s]
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, step, seats=seats, transcribed=transcribed)
        try:
            booking_id = booking_service.create_booking(
                user_id=uid, seat_id=seat["id"],
                members=ctx["members"], booking_date=ctx["date"],
                checkin=ctx["checkin_dt"], checkout=ctx["checkout_dt"],
            )
        except ValueError as e:
            r = str(e)
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, STEP_MAIN, transcribed=transcribed)

        r = llm_chat_service.booking_confirmed_message(
            name, seat_num, ctx["date"], ctx["checkin"], ctx["checkout"]
        )
        booking_info = {
            "booking_id": booking_id, "seat_number": seat_num,
            "members": ctx["members"], "date": ctx["date"],
            "checkin": ctx["checkin"], "checkout": ctx["checkout"],
        }
        background_tasks.add_task(whatsapp_service.send_booking_confirmation, user, booking_info)
        logging_service.log_event("booking_created", user_id=uid, booking_id=booking_id, seat=seat_num)
        auth_service.log_activity(uid, "create_booking", f"booking_id={booking_id} seat={seat_num}")

        session_service.clear_booking_context(uid)
        session_service.append_chat_message(uid, "assistant", r)
        return _reply(r, STEP_DONE, booking=booking_info, transcribed=transcribed)

    # ── Cancel flow ────────────────────────────────────────────────────────────

    if step == STEP_CANCEL_ALL:
        answer = re.sub(r"\s+", " ", msg.strip().lower())
        if answer in {"yes", "yes cancel all", "confirm", "confirm cancel all"}:
            cancelled = 0
            for bid in ctx.get("booking_ids", []):
                try:
                    booking = booking_service.cancel_booking(bid, uid)
                    background_tasks.add_task(whatsapp_service.send_cancellation_confirmation, user, booking)
                    logging_service.log_event("booking_cancelled", user_id=uid, booking_id=bid)
                    auth_service.log_activity(uid, "cancel_booking", f"booking_id={bid}")
                    cancelled += 1
                except (ValueError, PermissionError):
                    continue
            session_service.clear_booking_context(uid)
            r = f"Cancelled {cancelled} booking(s) successfully."
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, STEP_MAIN, transcribed=transcribed)
        if answer in {"no", "nope", "cancel", "keep"}:
            session_service.clear_booking_context(uid)
            r = "No bookings were cancelled."
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, STEP_MAIN, transcribed=transcribed)
        r = "Please reply exactly 'YES CANCEL ALL' to cancel every active booking, or 'NO' to keep them."
        session_service.append_chat_message(uid, "assistant", r)
        return _reply(r, STEP_CANCEL_ALL, transcribed=transcribed)

    if step == STEP_CANCEL:
        # User is choosing which booking to cancel
        active = [b for b in booking_service.get_bookings_by_user(uid) if b["status"] == "confirmed"]
        if _wants_cancel_all(msg):
            ctx_new = {"step": STEP_CANCEL_ALL, "booking_ids": [b["id"] for b in active]}
            session_service.set_booking_context(uid, ctx_new)
            r = _cancel_all_prompt(len(active))
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, STEP_CANCEL_ALL, transcribed=transcribed)
        nums = re.findall(r"\d+", msg)
        if not nums:
            r = "Please reply with a booking number, e.g. 'cancel #21'."
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, step, transcribed=transcribed)
        if len(nums) > 1:
            r = "Please choose one booking number only, for example 'cancel #7'. Or say 'cancel all bookings'."
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, step, transcribed=transcribed)
        bid = int(nums[0])
        try:
            booking = booking_service.cancel_booking(bid, uid)
            background_tasks.add_task(whatsapp_service.send_cancellation_confirmation, user, booking)
            logging_service.log_event("booking_cancelled", user_id=uid, booking_id=bid)
            auth_service.log_activity(uid, "cancel_booking", f"booking_id={bid}")
            r = llm_chat_service.booking_cancelled()
            ctx = {}
            session_service.set_booking_context(uid, ctx)
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, STEP_MAIN, transcribed=transcribed)
        except PermissionError as e:
            logger.warning("Unauthorized cancellation attempt: booking=%s user=%s", bid, uid)
            r = "You can only cancel your own bookings."
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, STEP_MAIN, transcribed=transcribed)
        except ValueError as e:
            r = str(e)
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, STEP_MAIN, transcribed=transcribed)

    # ── Main menu / intent routing ─────────────────────────────────────────────

    intent = _detect_intent(msg)

    if intent == "book":
        ctx = {"step": STEP_MEMBERS}
        r, next_step, seats = _continue_booking(ctx, msg)
        if next_step == STEP_MAIN:
            session_service.clear_booking_context(uid)
        else:
            session_service.set_booking_context(uid, ctx)
        session_service.append_chat_message(uid, "assistant", r)
        return _reply(r, next_step, seats=seats, transcribed=transcribed)

    if intent == "my_bookings":
        bookings = booking_service.get_bookings_by_user(uid)
        if not bookings:
            r = "You have no bookings yet. Say 'book a table' to get started!"
        else:
            lines = [f"Here are your bookings ({name}):"]
            for b in bookings[:10]:
                ci = str(b.get("checkin_time", ""))[:16]
                co = str(b.get("checkout_time", ""))[:16]
                lines.append(f"  #{b['id']} — Seat {b['seat_number']} | {b['booking_date']} {ci[:11]}–{co[11:]} | {b['status'].upper()}")
            r = "\n".join(lines)
        session_service.append_chat_message(uid, "assistant", r)
        return _reply(r, STEP_MAIN, transcribed=transcribed)

    if intent == "cancel":
        # Check for specific booking id in message
        nums = re.findall(r"\d+", msg)
        active = [b for b in booking_service.get_bookings_by_user(uid) if b["status"] == "confirmed"]
        if not active:
            r = "You have no active bookings to cancel."
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, STEP_MAIN, transcribed=transcribed)
        if _wants_cancel_all(msg):
            ctx_new = {"step": STEP_CANCEL_ALL, "booking_ids": [b["id"] for b in active]}
            session_service.set_booking_context(uid, ctx_new)
            r = _cancel_all_prompt(len(active))
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, STEP_CANCEL_ALL, transcribed=transcribed)
        if nums:
            if len(nums) > 1:
                r = "Please choose one booking number only, for example 'cancel #7'. Or say 'cancel all bookings'."
                session_service.append_chat_message(uid, "assistant", r)
                return _reply(r, STEP_MAIN, transcribed=transcribed)
            bid = int(nums[0])
            try:
                booking = booking_service.cancel_booking(bid, uid)
                background_tasks.add_task(whatsapp_service.send_cancellation_confirmation, user, booking)
                logging_service.log_event("booking_cancelled", user_id=uid, booking_id=bid)
                auth_service.log_activity(uid, "cancel_booking", f"booking_id={bid}")
                r = llm_chat_service.booking_cancelled()
                session_service.append_chat_message(uid, "assistant", r)
                return _reply(r, STEP_MAIN, transcribed=transcribed)
            except PermissionError:
                r = "You can only cancel your own bookings."
                session_service.append_chat_message(uid, "assistant", r)
                return _reply(r, STEP_MAIN, transcribed=transcribed)
            except ValueError as e:
                r = str(e)
                session_service.append_chat_message(uid, "assistant", r)
                return _reply(r, STEP_MAIN, transcribed=transcribed)
        if len(active) == 1:
            booking = booking_service.cancel_booking(active[0]["id"], uid)
            background_tasks.add_task(whatsapp_service.send_cancellation_confirmation, user, booking)
            logging_service.log_event("booking_cancelled", user_id=uid, booking_id=active[0]["id"])
            auth_service.log_activity(uid, "cancel_booking", f"booking_id={active[0]['id']}")
            r = llm_chat_service.booking_cancelled()
            session_service.append_chat_message(uid, "assistant", r)
            return _reply(r, STEP_MAIN, transcribed=transcribed)
        # Multiple — ask which
        ctx_new = {"step": STEP_CANCEL}
        session_service.set_booking_context(uid, ctx_new)
        r = llm_chat_service.ask_which_booking(active)
        session_service.append_chat_message(uid, "assistant", r)
        return _reply(r, STEP_CANCEL, transcribed=transcribed)

    # ── Free conversation ──────────────────────────────────────────────────────
    history = session_service.get_chat_history(uid, limit=8)
    r = llm_chat_service.free_chat(name, msg, history)
    session_service.append_chat_message(uid, "assistant", r)
    return _reply(r, STEP_MAIN, transcribed=transcribed)


@router.post("/chat/reset")
async def reset_chat(request: Request, token: str | None = Form(default=None)):
    auth_header = request.headers.get("Authorization", "")
    token = token or (auth_header[7:] if auth_header.startswith("Bearer ") else "")
    user = auth_service.get_user_from_token(token)
    if user:
        session_service.clear_booking_context(user["id"])
    return {"status": "reset"}
