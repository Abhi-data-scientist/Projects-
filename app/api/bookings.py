import logging
from fastapi import APIRouter, Form, HTTPException, BackgroundTasks, Request

from services import auth_service, booking_service, logging_service, whatsapp_service

logger = logging.getLogger("bookings_api")
router = APIRouter(prefix="/bookings", tags=["bookings"])


def _resolve_user(request: Request, token: str = None):
    t = token
    if not t:
        auth = request.headers.get("Authorization", "")
        t = auth[7:] if auth.startswith("Bearer ") else request.query_params.get("token", "")
    user = auth_service.get_user_from_token(t)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


@router.get("/my")
async def my_bookings(request: Request):
    user = _resolve_user(request)
    bookings = booking_service.get_bookings_by_user(user["id"])
    return {"bookings": bookings}


@router.post("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    token: str = Form(default=None),
):
    user = _resolve_user(request, token)
    try:
        booking = booking_service.cancel_booking(booking_id, user["id"])
        background_tasks.add_task(whatsapp_service.send_cancellation_confirmation, user, booking)
        logging_service.log_event("booking_cancelled", user_id=user["id"], booking_id=booking_id)
        auth_service.log_activity(user["id"], "cancel_booking", f"booking_id={booking_id}")
        logger.info("Booking %s cancelled by user %s", booking_id, user["id"])
        return {"status": "cancelled", "booking_id": booking_id}
    except PermissionError as e:
        logger.warning("Unauthorized cancellation attempt: booking=%s user=%s", booking_id, user["id"])
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Cancel booking error: %s", e)
        raise HTTPException(status_code=500, detail="Cancellation failed.")
