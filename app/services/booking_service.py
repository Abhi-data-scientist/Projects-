import logging
from datetime import datetime

from core.database import execute_insert, execute_query, execute_select
from services.redis_client import rjson_get, rjson_set, rdelete

logger = logging.getLogger("booking_service")
_BOOKINGS_TTL = 3600


# ── Seat grid (for display) ───────────────────────────────────────────────────

def get_all_seats() -> list[dict]:
    return execute_select(
        "SELECT id, seat_number, seat_type, capacity, description, status "
        "FROM seats ORDER BY seat_number"
    )


# ── Overlap-based availability ────────────────────────────────────────────────

def get_available_seats(date: str, checkin_dt: str, checkout_dt: str, min_capacity: int = 1) -> list[dict]:
    """
    Returns seats that have capacity >= min_capacity AND no confirmed booking
    that overlaps the requested [checkin_dt, checkout_dt] on the given date.
    """
    return execute_select(
        """
        SELECT s.id, s.seat_number, s.seat_type, s.capacity, s.description
        FROM seats s
        WHERE s.capacity >= %s
          AND s.id NOT IN (
              SELECT b.seat_id FROM bookings b
              WHERE b.booking_date = %s
                AND b.status = 'confirmed'
                AND b.checkin_time  < %s
                AND b.checkout_time > %s
          )
        ORDER BY s.seat_number
        """,
        (min_capacity, date, checkout_dt, checkin_dt),
    )


def get_seat_availability(date: str, checkin: str, checkout: str, members: int = 1) -> list[dict]:
    """Return seats free for the requested interval, accepting HH:MM inputs."""
    checkin_dt = checkin if " " in checkin else f"{date} {checkin}:00"
    checkout_dt = checkout if " " in checkout else f"{date} {checkout}:00"
    return get_available_seats(date, checkin_dt, checkout_dt, members)


def get_seat_by_id(seat_id: int) -> dict | None:
    rows = execute_select("SELECT * FROM seats WHERE id=%s LIMIT 1", (seat_id,))
    return rows[0] if rows else None


def get_seat_by_number(seat_number: str) -> dict | None:
    rows = execute_select("SELECT * FROM seats WHERE seat_number=%s LIMIT 1", (seat_number,))
    return rows[0] if rows else None


# ── Bookings ──────────────────────────────────────────────────────────────────

def create_booking(user_id: int, seat_id: int, members: int,
                   booking_date: str, checkin: str, checkout: str) -> int:
    # Double-check availability inside a transaction
    conflict = execute_select(
        """
        SELECT id FROM bookings
        WHERE seat_id=%s AND booking_date=%s AND status='confirmed'
          AND checkin_time < %s AND checkout_time > %s
        LIMIT 1
        """,
        (seat_id, booking_date, checkout, checkin),
    )
    if conflict:
        raise ValueError("Seat just got booked by someone else. Please pick another.")

    booking_id = execute_insert(
        """INSERT INTO bookings
           (user_id, seat_id, members_count, booking_date, checkin_time, checkout_time)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (user_id, seat_id, members, booking_date, checkin, checkout),
    )
    # The status column is only a present-time display hint. Time-slot
    # availability always comes from the overlap query above.
    _refresh_seat_status(seat_id)
    # Invalidate user bookings cache
    rdelete(f"user:{user_id}:bookings")
    logger.info("Booking created id=%s user=%s seat=%s", booking_id, user_id, seat_id)
    return booking_id


def get_bookings_by_user(user_id: int) -> list[dict]:
    # Try cache first
    cached = rjson_get(f"user:{user_id}:bookings")
    if cached is not None:
        return cached
    rows = execute_select(
        """SELECT b.id, b.members_count, b.booking_date, b.checkin_time,
                  b.checkout_time, b.status, b.created_at,
                  s.seat_number, s.seat_type, s.description
           FROM bookings b JOIN seats s ON b.seat_id = s.id
           WHERE b.user_id=%s ORDER BY b.created_at DESC""",
        (user_id,),
    )
    # Serialize datetime fields
    clean = []
    for r in rows:
        d = dict(r)
        for k, v in d.items():
            if hasattr(v, 'strftime'):
                d[k] = str(v)
        clean.append(d)
    rjson_set(f"user:{user_id}:bookings", clean, _BOOKINGS_TTL)
    return clean


def get_booking_by_id(booking_id: int) -> dict | None:
    rows = execute_select(
        """SELECT b.*, s.seat_number FROM bookings b
           JOIN seats s ON b.seat_id=s.id WHERE b.id=%s LIMIT 1""",
        (booking_id,),
    )
    if not rows:
        return None
    d = dict(rows[0])
    for k, v in d.items():
        if hasattr(v, 'strftime'):
            d[k] = str(v)
    return d


def cancel_booking(booking_id: int, user_id: int) -> dict | None:
    booking = get_booking_by_id(booking_id)
    if not booking:
        raise ValueError("Booking not found.")
    if booking["user_id"] != user_id:
        raise PermissionError("You can only cancel your own bookings.")
    if booking["status"] != "confirmed":
        raise ValueError(f"Booking is already {booking['status']}.")

    execute_query("UPDATE bookings SET status='cancelled' WHERE id=%s", (booking_id,))
    # Free the seat if no other active booking overlaps at this moment
    _refresh_seat_status(booking["seat_id"])
    rdelete(f"user:{user_id}:bookings")
    logger.info("Booking %s cancelled by user %s", booking_id, user_id)
    return booking


def _refresh_seat_status(seat_id: int):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    active = execute_select(
        "SELECT id FROM bookings WHERE seat_id=%s AND status='confirmed' "
        "AND checkin_time <= %s AND checkout_time > %s LIMIT 1",
        (seat_id, now, now),
    )
    status = "booked" if active else "available"
    execute_query("UPDATE seats SET status=%s WHERE id=%s", (status, seat_id))


# ── Auto-expire (scheduler) ───────────────────────────────────────────────────

def expire_old_bookings():
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expired = execute_select(
            "SELECT id, seat_id, user_id FROM bookings "
            "WHERE status='confirmed' AND checkout_time <= %s",
            (now,),
        )
        for row in expired:
            execute_query("UPDATE bookings SET status='completed' WHERE id=%s", (row["id"],))
            execute_query("UPDATE seats SET status='available' WHERE id=%s", (row["seat_id"],))
            rdelete(f"user:{row['user_id']}:bookings")
            logger.info("Booking %s expired — seat %s freed.", row["id"], row["seat_id"])
    except Exception as exc:
        logger.error("expire_old_bookings failed: %s", exc)
