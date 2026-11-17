"""
Generates and inserts seed data:
  10,000 customers
  1,000 products
  100,000 orders
  500,000 order_items

Simple plain Python, batched inserts with mysql-connector.
Run with: python -m app.seed.generate_data
"""

import random
import datetime
import mysql.connector
from core.config import settings

FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Isha", "Ananya", "Diya", "Kabir", "Sara",
               "Reyansh", "Myra", "Arjun", "Priya", "Rohan", "Neha", "Karan", "Meera"]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Bairwa", "Singh", "Kumar", "Patel", "Yadav",
              "Reddy", "Nair", "Iyer", "Chauhan", "Mehta", "Joshi"]
CITIES = ["Jaipur", "Delhi", "Mumbai", "Bengaluru", "Hyderabad", "Chennai",
          "Kolkata", "Pune", "Ahmedabad", "Lucknow", "Surat", "Indore"]
CATEGORIES = ["Electronics", "Fashion", "Home & Kitchen", "Books", "Beauty",
              "Sports", "Toys", "Grocery", "Automotive", "Furniture"]

BATCH_SIZE = 5000


def get_conn():
    return mysql.connector.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DATABASE,
    )


def create_schema(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(150),
            city VARCHAR(50),
            signup_date DATE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INT AUTO_INCREMENT PRIMARY KEY,
            product_name VARCHAR(150),
            category VARCHAR(50),
            price DECIMAL(10,2)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INT AUTO_INCREMENT PRIMARY KEY,
            customer_id INT,
            order_date DATE,
            total_amount DECIMAL(12,2),
            INDEX idx_customer (customer_id),
            INDEX idx_order_date (order_date)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT,
            product_id INT,
            quantity INT,
            amount DECIMAL(10,2),
            INDEX idx_order (order_id),
            INDEX idx_product (product_id)
        )
    """)


def random_date(start_year=2023, end_year=2026):
    start = datetime.date(start_year, 1, 1)
    end = datetime.date(end_year, 8, 31)
    delta = (end - start).days
    return start + datetime.timedelta(days=random.randint(0, delta))


def seed_customers(cursor, conn, count=10000):
    print(f"Seeding {count} customers...")
    batch = []
    for i in range(count):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        email = f"user{i+1}@example.com"
        city = random.choice(CITIES)
        signup = random_date()
        batch.append((name, email, city, signup))
        if len(batch) >= BATCH_SIZE:
            cursor.executemany(
                "INSERT INTO customers (name, email, city, signup_date) VALUES (%s,%s,%s,%s)",
                batch,
            )
            conn.commit()
            batch = []
    if batch:
        cursor.executemany(
            "INSERT INTO customers (name, email, city, signup_date) VALUES (%s,%s,%s,%s)",
            batch,
        )
        conn.commit()
    print("Customers done.")


def seed_products(cursor, conn, count=1000):
    print(f"Seeding {count} products...")
    batch = []
    for i in range(count):
        category = random.choice(CATEGORIES)
        name = f"{category} Item {i+1}"
        price = round(random.uniform(99, 49999), 2)
        batch.append((name, category, price))
        if len(batch) >= BATCH_SIZE:
            cursor.executemany(
                "INSERT INTO products (product_name, category, price) VALUES (%s,%s,%s)",
                batch,
            )
            conn.commit()
            batch = []
    if batch:
        cursor.executemany(
            "INSERT INTO products (product_name, category, price) VALUES (%s,%s,%s)",
            batch,
        )
        conn.commit()
    print("Products done.")


def seed_orders_and_items(cursor, conn, customer_count=10000, product_count=1000,
                           order_count=100000, avg_items_per_order=5):
    print(f"Seeding {order_count} orders and ~{order_count * avg_items_per_order} order_items...")
    order_batch = []
    for i in range(order_count):
        customer_id = random.randint(1, customer_count)
        order_date = random_date()
        # placeholder total, corrected after items are known
        order_batch.append((customer_id, order_date, 0))
        if len(order_batch) >= BATCH_SIZE:
            _flush_orders_and_items(cursor, conn, order_batch, product_count)
            order_batch = []
    if order_batch:
        _flush_orders_and_items(cursor, conn, order_batch, product_count)
    print("Orders and order_items done.")


def _flush_orders_and_items(cursor, conn, order_batch, product_count):
    cursor.executemany(
        "INSERT INTO orders (customer_id, order_date, total_amount) VALUES (%s,%s,%s)",
        order_batch,
    )
    conn.commit()

    # mysql-connector reports the *first* generated AUTO_INCREMENT id for
    # executemany().  The orders in this batch are consecutive, so the
    # remaining ids can be derived from it.
    first_id_in_batch = cursor.lastrowid

    item_batch = []
    order_totals = {}

    for idx in range(len(order_batch)):
        order_id = first_id_in_batch + idx
        num_items = random.randint(1, 8)
        total = 0.0
        for _ in range(num_items):
            product_id = random.randint(1, product_count)
            quantity = random.randint(1, 5)
            amount = round(random.uniform(99, 9999) * quantity, 2)
            total += amount
            item_batch.append((order_id, product_id, quantity, amount))
        order_totals[order_id] = round(total, 2)

    cursor.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, amount) VALUES (%s,%s,%s,%s)",
        item_batch,
    )
    conn.commit()

    update_batch = [(total, oid) for oid, total in order_totals.items()]
    cursor.executemany(
        "UPDATE orders SET total_amount = %s WHERE order_id = %s",
        update_batch,
    )
    conn.commit()


def main():
    conn = get_conn()
    cursor = conn.cursor()

    create_schema(cursor)
    conn.commit()

    seed_customers(cursor, conn, count=10000)
    seed_products(cursor, conn, count=1000)
    seed_orders_and_items(cursor, conn, customer_count=10000, product_count=1000, order_count=100000)

    cursor.close()
    conn.close()
    print("Seeding complete.")


if __name__ == "__main__":
    main()
