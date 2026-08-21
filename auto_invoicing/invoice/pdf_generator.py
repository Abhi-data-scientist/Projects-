import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import STORAGE_DIR, COMPANY_NAME, COMPANY_ADDRESS, COMPANY_GSTIN


def generate_invoice_pdf(invoice_no: str, calc: dict, customer: dict, due_date: str | None, order_reference: str | None) -> str:
    """
    calc: calculator.calculate_totals() ka output (line_items, subtotal, tax_rate, tax_amount, total_amount)
    customer: {name, email, phone, address}
    Return: generated PDF ka file path
    """
    pdf_filename = f"{invoice_no}.pdf"
    pdf_path = os.path.join(STORAGE_DIR, pdf_filename)
    document = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.fontSize = 9
    body.leading = 12
    heading = styles["Heading1"]
    heading.textColor = colors.HexColor("#0F172A")

    company_details = f"<b>{COMPANY_NAME}</b><br/>{COMPANY_ADDRESS}"
    if COMPANY_GSTIN:
        company_details += f"<br/>GSTIN: {COMPANY_GSTIN}"
    customer_details = f"<b>Bill To</b><br/><b>{customer.get('name') or ''}</b>"
    for value in (customer.get("email"), customer.get("phone"), customer.get("address")):
        if value:
            customer_details += f"<br/>{value}"
    invoice_details = f"<b>INVOICE</b><br/>Invoice No: {invoice_no}<br/>Date: {date.today().isoformat()}"
    if due_date:
        invoice_details += f"<br/>Due Date: {due_date}"
    if order_reference:
        invoice_details += f"<br/>Order Ref: {order_reference}"

    story = [Paragraph("INVOICE", heading), Spacer(1, 5 * mm)]
    info = Table(
        [[Paragraph(company_details, body), Paragraph(customer_details, body), Paragraph(invoice_details, body)]],
        colWidths=[58 * mm, 58 * mm, 48 * mm],
    )
    info.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.extend([info, Spacer(1, 9 * mm)])

    rows = [["Description", "Qty", "Unit Price", "Line Total"]]
    for item in calc["line_items"]:
        rows.append([
            item["description"],
            str(item["quantity"]),
            f"Rs. {item['unit_price']:.2f}",
            f"Rs. {item['line_total']:.2f}",
        ])
    items_table = Table(rows, colWidths=[82 * mm, 20 * mm, 31 * mm, 31 * mm], repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([items_table, Spacer(1, 7 * mm)])

    totals = [
        ["Subtotal", f"Rs. {calc['subtotal']:.2f}"],
        [f"Tax ({calc['tax_rate']}%)", f"Rs. {calc['tax_amount']:.2f}"],
        ["Total", f"Rs. {calc['total_amount']:.2f}"],
    ]
    totals_table = Table(totals, colWidths=[35 * mm, 35 * mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(totals_table)
    document.build(story)

    return pdf_path
