import logging
from core.config import settings
from services.groq_service import generate_text

logger = logging.getLogger("llm_chat_service")

_SYS = (
    "You are Bristo, a warm and friendly AI assistant for a stylish urban cafe. "
    "Keep replies short (2-3 sentences), conversational and enthusiastic. "
    "Plain text only — no markdown, no asterisks."
)


def _llm(prompt: str, fallback: str, temperature: float = 0.7) -> str:
    if not settings.ENABLE_LLM:
        return fallback
    try:
        return generate_text(f"{_SYS}\n\n{prompt}", temperature=temperature)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return fallback


# ── LLM calls (kept) ─────────────────────────────────────────────────────────

def welcome_back(name: str, booking_count: int) -> str:
    return _llm(
        f"Welcome back {name}! They have made {booking_count} booking(s) before. "
        "Greet them warmly, thank them for returning, and offer to help.",
        f"Welcome back, {name}! How can I help with your next cafe visit?",
    )


def new_user_welcome(name: str) -> str:
    return _llm(
        f"Welcome {name} as a brand new guest. Express excitement and ask how you can help.",
        f"Welcome, {name}! I can help you book a table or check your bookings.",
    )


def booking_confirmed_message(name: str, seat_number: str, date: str, checkin: str, checkout: str) -> str:
    return _llm(
        f"Booking confirmed for {name}! Seat {seat_number} on {date} from {checkin} to {checkout}. "
        "Congratulate them warmly and wish them a great visit.",
        f"All set, {name}! Seat {seat_number} is confirmed for {date}, {checkin} to {checkout}. We look forward to seeing you!",
    )


def free_chat(user_name: str, user_message: str, history: list) -> str:
    msgs = history[-8:] if len(history) > 8 else history
    ctx = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in msgs)
    prompt = (
        f"Cafe assistant chatting with {user_name}.\n"
        f"Recent conversation:\n{ctx}\n"
        f"User: {user_message}\n"
        "Respond helpfully as Bristo."
    )
    return _llm(prompt, "I can help you book a table, view your bookings, or cancel a reservation.")


# ── Static fast responses (no LLM) ───────────────────────────────────────────

def ask_members() -> str:
    return "How many people will be joining? (e.g. 2 or 4)"


def ask_date() -> str:
    return "What date would you like to book? (DD-MM-YYYY or say the date, e.g. 5 September)"


def ask_checkin() -> str:
    return "What time will you check in? (e.g. 14:00 or 2 PM)"


def ask_checkout() -> str:
    return "What time will you check out? (e.g. 18:00 or 6 PM)"


def ask_seat_selection(count: int) -> str:
    return f"Here are {count} available seat(s). Please type the seat number to select one."


def no_seats_available() -> str:
    return "Sorry, no seats are available for that time slot. Please try a different time or date."


def seat_not_available(num: str) -> str:
    return f"Seat {num} is not available or does not exist. Please choose from the list above."


def invalid_date() -> str:
    return "Please provide a valid date. For example: 05-09-2026 or say '5 September 2026'."


def invalid_time() -> str:
    return "Please provide a valid time. For example: 14:00 or say '2 PM'."


def booking_cancelled() -> str:
    return "Your booking has been cancelled successfully. We hope to see you again!"


def ask_which_booking(bookings: list) -> str:
    lines = ["You have multiple active bookings. Which one would you like to cancel?"]
    for b in bookings:
        checkin = str(b["checkin_time"]).split()[-1][:5]
        checkout = str(b["checkout_time"]).split()[-1][:5]
        lines.append(
            f"  #{b['id']} — Seat {b['seat_number']} on {b['booking_date']} "
            f"{checkin}–{checkout}"
        )
    lines.append("Reply with the booking number, e.g. 'cancel #21'.")
    return "\n".join(lines)
