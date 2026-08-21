"""
Step A + B: File type detect karke text nikalta hai.
- Text-based PDF -> pdfplumber (fast, free, accurate)
- Agar text bahut kam mila (scanned PDF) -> caller OCR fallback trigger karega
"""
import pdfplumber

MIN_CHARS_FOR_TEXT_PDF = 30  # isse kam text mila to samjho scanned hai


def extract_text_from_pdf(file_path: str) -> str:
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def is_text_sufficient(text: str) -> bool:
    return len(text.strip()) >= MIN_CHARS_FOR_TEXT_PDF
