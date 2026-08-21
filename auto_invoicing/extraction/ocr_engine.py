"""
Fallback OCR - jab pdfplumber se text nahi mila (scanned PDF) ya seedha image upload hui.
"""
import pytesseract
from PIL import Image
from pdf2image import convert_from_path


def ocr_from_image(file_path: str) -> str:
    image = Image.open(file_path)
    return pytesseract.image_to_string(image).strip()


def ocr_from_scanned_pdf(file_path: str) -> str:
    pages = convert_from_path(file_path, dpi=300)
    text_parts = [pytesseract.image_to_string(page) for page in pages]
    return "\n".join(text_parts).strip()
