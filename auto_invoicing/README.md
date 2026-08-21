# AI Auto-Invoicing System

Single endpoint: PDF/receipt upload karo → invoice PDF seedha response me milta hai.

## Workflow

```
Upload (PDF/image)
  -> Text extraction (pdfplumber, fallback OCR)
  -> Gemini structuring (JSON extraction only, no calculation)
  -> Validation (required fields check)
  -> Calculation (subtotal/tax/total -- Python code se, LLM se nahi)
  -> Duplicate lookup (DB hash lookup, duplicate uploads bhi generate honge)
  -> Invoice number generation
  -> PDF generation (WeasyPrint)
  -> MySQL storage (customers, invoices, invoice_items)
  -> Response: PDF direct
```

## Setup

### 1. System dependencies (OCR ke liye)
- **Tesseract OCR** install karo: https://github.com/UB-Mannheim/tesseract/wiki (Windows)
- **Poppler** install karo (pdf2image ke liye): https://github.com/oschwartz10612/poppler-windows/releases
  - Dono ko system PATH me add karna hoga.

### 2. Python setup
```bash
pip install -r requirements.txt
```

> Note: WeasyPrint ko Windows pe GTK3 runtime chahiye hota hai (https://weasyprint.org/start/). Agar install me dikkat aaye to batana, alternative (xhtml2pdf) switch kar denge.

### 3. Database
```bash
mysql -u root -p < database/schema.sql
```

### 4. Environment variables
`.env.example` ko `.env` me copy karo aur values fill karo:
```bash
cp .env.example .env
```

### 5. Run
```bash
python run.py
```
Server: `http://localhost:8000`

## Test karne ke liye

### Single file

```bash
curl -X POST http://localhost:8000/api/invoices/upload \
  -F "file=@sample_receipt.pdf" \
  --output invoice.pdf
```

### Bulk files

Multiple PDF/image files ek saath bhejne ke liye `files` field ko repeat karein. Response me `generated-invoices.zip` milegi. ZIP ke andar har generated PDF source file ke same base name ke saath `_invoice` laga kar hogi; jaise `receipt_1.jpg` ka invoice `receipt_1_invoice.pdf` hoga. `processing-results.json` mein successful aur failed files ka summary milega.

Browser se bina IDs/URLs copy kiye bulk upload karna ho to server run karne ke baad `http://localhost:8000/bulk-upload` kholein. Files select karke upload karein; invoices alag-alag automatically download hongi. Browser ek baar multiple downloads allow karne ki permission maang sakta hai.

```bash
curl -X POST http://localhost:8000/api/invoices/upload-bulk \
  -F "files=@receipt_1.pdf" \
  -F "files=@receipt_2.jpg" \
  --output bulk-results.json
```

## Logs

- `logs/app.log` — normal debug/error logs
- `logs/pipeline.jsonl` — har request ke har stage ka structured log (JSON lines), format:
```json
{"request_id": "...", "stage": "llm_extraction", "status": "success", "timestamp": ..., "detail": {...}}
```
Isse dekh sakte ho koi specific request kis stage pe fail hui, aur kitna time laga.

## Config flags (`config.py` / `.env`)

- `STRICT_VALIDATION=true` — customer_name ya items missing hone pe `422` error dega.
  `false` karne pe best-effort invoice ban jaayega jo bhi mila usi se.
- `DEFAULT_TAX_RATE` — agar document me tax rate na mile to ye default use hoga.
