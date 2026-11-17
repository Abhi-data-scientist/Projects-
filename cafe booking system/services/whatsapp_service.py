"""Optional Twilio WhatsApp notifications for booking events."""

import logging
import re

import httpx

from core.config import settings
from services import logging_service

logger = logging.getLogger("whatsapp_service")


def _whatsapp_address(phone: str) -> str:
    """Return a Twilio WhatsApp address only for E.164 phone numbers."""
    phone = (phone or "").strip().replace(" ", "")
    if phone.startswith("whatsapp:"):
        phone = phone[9:]
    return f"whatsapp:{phone}" if re.fullmatch(r"\+[1-9]\d{7,14}", phone) else ""


def _send(phone: str, body: str):
    sender = _whatsapp_address(settings.TWILIO_WHATSAPP_FROM)
    recipient = _whatsapp_address(phone)
    if not all((settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, sender, recipient)):
        logger.info("Twilio WhatsApp is not configured or user phone is invalid; notification skipped.")
        return
    try:
        response = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
            data={"From": sender, "To": recipient, "Body": body},
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=10,
        )
        response.raise_for_status()
        logger.info("WhatsApp notification queued for %s", recipient)
        logging_service.log_event("whatsapp_notification_queued", notification_type=body.split("!", 1)[0])
    except httpx.HTTPError as exc:
        # Notifications must never undo a successful booking or cancellation.
        logger.error("WhatsApp notification failed: %s", exc)
        logging_service.log_event("whatsapp_notification_failed")


def send_booking_confirmation(user: dict, booking: dict):
    _send(
        user.get("phone", ""),
        f"Cafe Booking confirmed! Booking #{booking['booking_id']}: seat {booking['seat_number']}, "
        f"{booking['date']} from {booking['checkin']} to {booking['checkout']}.",
    )


def send_cancellation_confirmation(user: dict, booking: dict):
    _send(
        user.get("phone", ""),
        f"Cafe Booking cancelled: booking #{booking.get('id', booking.get('booking_id', ''))}, "
        f"seat {booking.get('seat_number', '')} on {booking.get('booking_date', booking.get('date', ''))}.",
    )
