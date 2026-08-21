import mysql.connector

from app.config import DB_CONFIG


def get_connection():
    """Open a fresh MySQL connection using raw mysql-connector (no ORM)."""
    return mysql.connector.connect(**DB_CONFIG)


def fetch_all_products():
    """
    Fetch all products from the database as a list of dicts.
    Used to build the TF-IDF corpus and to run filtering/ranking against.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT product_id, name, description, price, category, brand, color
        FROM products
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows
