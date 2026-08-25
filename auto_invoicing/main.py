import io
import json
import os
import shutil
import zipfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from config import STRICT_VALIDATION, UPLOAD_DIR
from database.connection import get_connection
from database.queries import (
    check_duplicate_invoice,
    find_or_create_customer,
    generate_next_invoice_number,
    save_invoice,
)
from extraction.llm_structurer import extract_invoice_data_from_document
from extraction.nlp_extractor import extract_invoice_data_with_nlp, has_minimum_invoice_data
from extraction.ocr_engine import ocr_from_image, ocr_from_scanned_pdf
from extraction.text_extractor import extract_text_from_pdf, is_text_sufficient
from invoice.pdf_generator import generate_invoice_pdf
from utils.logger import log_stage, logger, new_request_id
from validation.calculator import calculate_totals, compute_duplicate_hash, normalize_date, validate_required_fields

app = FastAPI(title="AI Auto-Invoicing System")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MIME_TYPES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


async def process_invoice(file: UploadFile) -> dict:
    """Run the invoice pipeline for one upload and return generated PDF details."""
    request_id = new_request_id()
    filename = file.filename or "upload"
    log_stage(request_id, "upload_received", "started", {"filename": filename})

    ext = os.path.splitext(filename)[1].lower()
    if ext != ".pdf" and ext not in IMAGE_EXTENSIONS:
        log_stage(request_id, "upload_received", "failed", {"reason": "unsupported file type"})
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext or 'unknown'}")

    saved_path = os.path.join(UPLOAD_DIR, f"{request_id}{ext}")
    with open(saved_path, "wb") as destination:
        shutil.copyfileobj(file.file, destination)
    log_stage(request_id, "upload_received", "success", {"saved_path": saved_path})

    try:
        log_stage(request_id, "text_extraction", "started")
        extraction_source = "pdfplumber"
        if ext == ".pdf":
            raw_text = extract_text_from_pdf(saved_path)
            if not is_text_sufficient(raw_text):
                logger.info(f"[{request_id}] text layer weak, falling back to OCR")
                raw_text = ocr_from_scanned_pdf(saved_path)
                extraction_source = "ocr"
        else:
            raw_text = ocr_from_image(saved_path)
            extraction_source = "ocr"

        if is_text_sufficient(raw_text):
            log_stage(request_id, "text_extraction", "success", {"source": extraction_source, "chars_extracted": len(raw_text)})
            log_stage(request_id, "nlp_regex_extraction", "started", {"source": extraction_source})
            extracted = extract_invoice_data_with_nlp(raw_text)
            log_stage(request_id, "nlp_regex_extraction", "success", {"extracted": extracted})
        else:
            log_stage(request_id, "text_extraction", "failed", {"source": extraction_source, "reason": "pdfplumber_and_ocr_text_insufficient"})
            extracted = None

        # Gemini is deliberately the final fallback: it reads the original file only
        # after local PDF extraction, OCR, Regex and NER could not produce an invoice.
        if extracted is None or not has_minimum_invoice_data(extracted):
            log_stage(request_id, "llm_fallback", "started", {"reason": "no_usable_local_invoice_data"})
            try:
                extracted = extract_invoice_data_from_document(saved_path, MIME_TYPES[ext])
            except ValueError as exc:
                log_stage(request_id, "llm_fallback", "failed", {"error": str(exc)})
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            log_stage(request_id, "llm_fallback", "success", {"extracted": extracted})

        try:
            due_date = normalize_date(extracted.get("due_date"))
        except ValueError as exc:
            # Due date is optional; don't let an unfamiliar LLM date format fail the whole invoice.
            due_date = None
            log_stage(request_id, "date_normalization", "failed", {"error": str(exc)})
        else:
            log_stage(request_id, "date_normalization", "success", {"due_date": due_date})

        log_stage(request_id, "validation", "started")
        issues = validate_required_fields(extracted)
        if issues and STRICT_VALIDATION:
            log_stage(request_id, "validation", "failed", {"issues": issues})
            raise HTTPException(
                status_code=422,
                detail={"message": "Invoice generate nahi ho saka, data incomplete hai.", "issues": issues},
            )
        log_stage(request_id, "validation", "success", {"issues": issues})

        calc = calculate_totals(extracted["items"], extracted.get("tax_rate_percent"))
        log_stage(request_id, "calculation", "success", calc)
        duplicate_hash = compute_duplicate_hash(
            extracted["customer_name"], calc["total_amount"], extracted.get("order_reference")
        )

        conn = get_connection()
        try:
            existing = check_duplicate_invoice(conn, duplicate_hash)
            if existing:
                # The same source document may be intentionally uploaded again.
                # Keep the hash for traceability, but always generate a fresh invoice.
                log_stage(
                    request_id,
                    "duplicate_check",
                    "success",
                    {"duplicate_of": existing["invoice_no"], "action": "generated_new_invoice"},
                )
            else:
                log_stage(request_id, "duplicate_check", "success")

            customer_id = find_or_create_customer(
                conn, extracted["customer_name"], extracted.get("customer_email"),
                extracted.get("customer_phone"), extracted.get("customer_address"),
            )
            invoice_no = generate_next_invoice_number(conn)
            log_stage(request_id, "invoice_numbering", "success", {"invoice_no": invoice_no})

            log_stage(request_id, "pdf_generation", "started")
            pdf_path = generate_invoice_pdf(
                invoice_no, calc,
                {
                    "name": extracted["customer_name"],
                    "email": extracted.get("customer_email"),
                    "phone": extracted.get("customer_phone"),
                    "address": extracted.get("customer_address"),
                },
                due_date, extracted.get("order_reference"),
            )
            log_stage(request_id, "pdf_generation", "success", {"pdf_path": pdf_path})

            log_stage(request_id, "db_storage", "started")
            save_invoice(
                conn, invoice_no, customer_id, calc["subtotal"], calc["tax_rate"],
                calc["tax_amount"], calc["total_amount"], due_date,
                extracted.get("order_reference"), duplicate_hash, pdf_path, saved_path,
                request_id, calc["line_items"],
            )
            log_stage(request_id, "db_storage", "success")
        finally:
            conn.close()

        log_stage(request_id, "pipeline_complete", "success", {"invoice_no": invoice_no})
        return {"invoice_no": invoice_no, "pdf_path": pdf_path}
    except HTTPException:
        raise
    except Exception as exc:
        log_stage(request_id, "pipeline_error", "failed", {"error": str(exc)})
        logger.exception(f"[{request_id}] Unexpected error")
        raise HTTPException(500, "Internal error while generating invoice.") from exc


@app.post("/api/invoices/upload")
async def upload_invoice(file: UploadFile = File(...)):
    """Generate one invoice PDF from a single PDF or image upload."""
    result = await process_invoice(file)
    return FileResponse(result["pdf_path"], media_type="application/pdf", filename=f"{result['invoice_no']}.pdf")


@app.post("/api/invoices/upload-bulk")
async def upload_invoices_bulk(files: list[UploadFile] = File(...)):
    """Generate invoices from multiple uploads and return them in one ZIP file."""
    if not files:
        raise HTTPException(400, "Kam se kam ek file upload karein.")

    results = {"successful": [], "failed": []}
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            original_name = file.filename or "upload"
            zip_name = f"{os.path.splitext(os.path.basename(original_name))[0] or 'invoice'}_invoice.pdf"
            try:
                result = await process_invoice(file)
                zip_file.write(result["pdf_path"], arcname=zip_name)
                results["successful"].append({"source_file": original_name, "output_file": zip_name})
            except HTTPException as exc:
                results["failed"].append({
                    "source_file": original_name, "status_code": exc.status_code, "error": exc.detail,
                })
        zip_file.writestr("processing-results.json", json.dumps(results, ensure_ascii=False, indent=2, default=str))

    archive.seek(0)
    return StreamingResponse(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=generated-invoices.zip"},
    )


@app.get("/bulk-upload", response_class=HTMLResponse, include_in_schema=False)
def bulk_upload_page():
    """A browser page that downloads generated bulk invoices as one ZIP file."""
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bulk Invoice Upload</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; }
    main { max-width: 620px; margin: 72px auto; background: white; padding: 32px; border-radius: 12px; box-shadow: 0 8px 28px #0f172a1a; }
    h1 { margin-top: 0; } p { line-height: 1.5; color: #475569; }
    input { display: block; margin: 22px 0; width: 100%; }
    button { background: #2563eb; border: 0; border-radius: 7px; color: white; cursor: pointer; font-size: 16px; padding: 12px 18px; }
    button:disabled { background: #94a3b8; cursor: wait; }
    #status { margin-top: 20px; white-space: pre-line; }
    #downloads { border-top: 1px solid #e2e8f0; margin-top: 24px; padding-top: 20px; }
    #download-list { display: grid; gap: 8px; margin-top: 14px; }
    #download-list button { background: #eff6ff; color: #1d4ed8; font-size: 14px; padding: 9px 12px; text-align: left; }
  </style>
</head>
<body>
  <main>
    <h1>Bulk Invoice Upload</h1>
    <p>PDF ya image files select karein. Saari generated invoices ek ZIP file mein download hongi.</p>
    <form id="bulk-form">
      <input id="files" type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.webp" required>
      <button id="submit" type="submit">Upload and download ZIP</button>
    </form>
    <p id="status"></p>
    <section id="downloads" hidden>
      <button id="download-all" type="button">Download all invoices</button>
      <div id="download-list"></div>
    </section>
  </main>
  <script>
    const form = document.getElementById('bulk-form');
    const files = document.getElementById('files');
    const submit = document.getElementById('submit');
    const status = document.getElementById('status');
    const downloads = document.getElementById('downloads');
    const downloadAll = document.getElementById('download-all');
    const downloadList = document.getElementById('download-list');
    let generatedInvoices = [];

    function downloadInvoice(invoice) {
      const link = document.createElement('a');
      link.href = invoice.download_url;
      link.download = invoice.download_name;
      document.body.appendChild(link);
      link.click();
      link.remove();
    }

    downloadAll.addEventListener('click', () => {
      generatedInvoices.forEach((invoice, index) => setTimeout(() => downloadInvoice(invoice), index * 500));
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!files.files.length) return;
      submit.disabled = true;
      status.textContent = 'Invoices generate ho rahe hain...';
      downloads.hidden = true;
      downloadList.replaceChildren();
      const formData = new FormData();
      for (const file of files.files) formData.append('files', file);

      try {
        const response = await fetch('/api/invoices/upload-bulk', { method: 'POST', body: formData });
        if (!response.ok) {
          const result = await response.json();
          throw new Error(result.detail || 'Upload failed');
        }
        const archive = await response.blob();
        const downloadUrl = URL.createObjectURL(archive);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = 'generated-invoices.zip';
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(downloadUrl);
        status.textContent = 'ZIP download shuru ho gaya hai.';
        return;
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Upload failed');

        generatedInvoices = result.successful;
        result.successful.forEach((invoice) => {
          const invoiceButton = document.createElement('button');
          invoiceButton.type = 'button';
          invoiceButton.textContent = `Download ${invoice.download_name}`;
          invoiceButton.addEventListener('click', () => downloadInvoice(invoice));
          downloadList.appendChild(invoiceButton);
        });
        downloads.hidden = !result.successful.length;
        status.textContent = `${result.successful.length} invoice(s) generate ho chuki hain.` +
          (result.failed.length ? ` ${result.failed.length} file(s) process nahi ho saki.` : '') +
          (result.successful.length ? ' Neeche “Download all invoices” dabayein.' : '');
      } catch (error) {
        status.textContent = `Error: ${error.message}`;
      } finally {
        submit.disabled = false;
      }
    });
  </script>
</body>
</html>"""


@app.get("/health")
def health():
    return {"status": "ok"}


def custom_openapi():
    """Keep Swagger UI's bulk field as a file picker, not a text array."""
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(title=app.title, version="1.0.0", routes=app.routes)
    bulk_schema = schema["components"]["schemas"]["Body_upload_invoices_bulk_api_invoices_upload_bulk_post"]
    file_items = bulk_schema["properties"]["files"]["items"]
    file_items.pop("contentMediaType", None)
    file_items["format"] = "binary"
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
