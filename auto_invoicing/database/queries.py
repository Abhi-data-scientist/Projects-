from datetime import datetime

from database.connection import get_connection


def find_or_create_customer(conn, name: str, email: str | None, phone: str | None, address: str | None) -> int:
    with conn.cursor() as cur:
        if email:
            cur.execute("SELECT id FROM customers WHERE email = %s", (email,))
            row = cur.fetchone()
            if row:
                return row["id"]

        cur.execute(
            "INSERT INTO customers (name, email, phone, address) VALUES (%s, %s, %s, %s)",
            (name, email, phone, address),
        )
        return cur.lastrowid


def check_duplicate_invoice(conn, duplicate_hash: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, invoice_no, pdf_path FROM invoices WHERE duplicate_hash = %s LIMIT 1",
            (duplicate_hash,),
        )
        return cur.fetchone()


def generate_next_invoice_number(conn) -> str:
    """
    Sequential invoice number: INV-<year>-<seq>.
    FOR UPDATE lock lagate hain taaki concurrent requests me clash na ho.
    """
    year = datetime.now().year
    prefix = f"INV-{year}-"

    with conn.cursor() as cur:
        cur.execute(
            "SELECT invoice_no FROM invoices WHERE invoice_no LIKE %s ORDER BY id DESC LIMIT 1 FOR UPDATE",
            (f"{prefix}%",),
        )
        row = cur.fetchone()
        if row:
            last_seq = int(row["invoice_no"].split("-")[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1

    return f"{prefix}{next_seq:04d}"


def save_invoice(
    conn,
    invoice_no: str,
    customer_id: int,
    subtotal: float,
    tax_rate: float,
    tax_amount: float,
    total_amount: float,
    due_date: str | None,
    order_reference: str | None,
    duplicate_hash: str,
    pdf_path: str,
    source_file: str,
    request_id: str,
    line_items: list[dict],
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO invoices
                (invoice_no, customer_id, subtotal, tax_rate, tax_amount, total_amount,
                 due_date, order_reference, duplicate_hash, status, pdf_path, source_file, request_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'generated', %s, %s, %s)
            """,
            (
                invoice_no, customer_id, subtotal, tax_rate, tax_amount, total_amount,
                due_date, order_reference, duplicate_hash, pdf_path, source_file, request_id,
            ),
        )
        invoice_id = cur.lastrowid

        for item in line_items:
            cur.execute(
                """
                INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, line_total)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (invoice_id, item["description"], item["quantity"], item["unit_price"], item["line_total"]),
            )

    conn.commit()
    return invoice_id
