import logging
from core.database import get_connection, close_connection

logger = logging.getLogger("db_init")

# ── New / altered tables ──────────────────────────────────────────────────────
TABLES = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            name          VARCHAR(100) NOT NULL,
            phone         VARCHAR(20)  UNIQUE,
            email         VARCHAR(150) UNIQUE,
            password_hash VARCHAR(255),
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    "seats": """
        CREATE TABLE IF NOT EXISTS seats (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            seat_number VARCHAR(10)  NOT NULL UNIQUE,
            seat_type   ENUM('Window','Corner','Center','Lounge') DEFAULT 'Center',
            capacity    INT DEFAULT 4,
            description VARCHAR(200),
            status      ENUM('available','booked') DEFAULT 'available'
        )""",
    "bookings": """
        CREATE TABLE IF NOT EXISTS bookings (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            user_id       INT  NOT NULL,
            seat_id       INT  NOT NULL,
            members_count INT  NOT NULL,
            booking_date  DATE NOT NULL,
            checkin_time  DATETIME NOT NULL,
            checkout_time DATETIME NOT NULL,
            status        ENUM('confirmed','completed','cancelled') DEFAULT 'confirmed',
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (seat_id) REFERENCES seats(id)
        )""",
    "user_sessions": """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    INT NOT NULL,
            token      VARCHAR(64) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL,
            is_active  TINYINT(1) DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )""",
    "activity_logs": """
        CREATE TABLE IF NOT EXISTS activity_logs (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    INT,
            action     VARCHAR(100) NOT NULL,
            details    TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
}

# Columns to add if missing  (table, column, definition)
NEW_COLUMNS = [
    ("users", "email",         "VARCHAR(150) UNIQUE"),
    ("users", "password_hash", "VARCHAR(255)"),
]

SEATS_SEED = [
    ("A1", "Window",  2, "Cozy window seat with garden view"),
    ("A2", "Window",  2, "Bright window seat, perfect for working"),
    ("B1", "Corner",  4, "Quiet corner booth, great for groups"),
    ("B2", "Corner",  4, "Private corner table with sofa seating"),
    ("C1", "Center",  4, "Central table, lively atmosphere"),
    ("C2", "Center",  4, "Round table in the heart of the cafe"),
    ("C3", "Center",  6, "Large central table for bigger groups"),
    ("D1", "Lounge",  2, "Plush lounge sofa, ideal for a relaxed chat"),
    ("D2", "Lounge",  4, "Lounge area with coffee table"),
    ("D3", "Lounge",  6, "Premium lounge suite with extra space"),
]


def _col_exists(cursor, table, col):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (table, col),
    )
    return cursor.fetchone()[0] > 0


def setup_database():
    conn = cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Create tables
        for name, ddl in TABLES.items():
            cur.execute(ddl)
            logger.info("Table ready: %s", name)

        # Safe column additions
        for table, col, defn in NEW_COLUMNS:
            if not _col_exists(cur, table, col):
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
                logger.info("Added column %s.%s", table, col)

        # Phone numbers belonged to the old sign-up flow. Keep legacy values,
        # but allow new email/password-only accounts.
        cur.execute("ALTER TABLE users MODIFY COLUMN phone VARCHAR(20) NULL")

        # Seed seats
        for row in SEATS_SEED:
            cur.execute(
                "INSERT IGNORE INTO seats (seat_number, seat_type, capacity, description) VALUES (%s,%s,%s,%s)",
                row,
            )

        conn.commit()
        logger.info("DB migration complete.")
    except Exception as exc:
        if conn:
            conn.rollback()
        logger.error("DB migration failed: %s", exc)
        raise
    finally:
        close_connection(conn, cur)
