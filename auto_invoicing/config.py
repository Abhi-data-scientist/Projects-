import os
from dotenv import load_dotenv

load_dotenv()

# --- Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- MySQL ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "auto_invoicing")

# --- Business rules ---
DEFAULT_TAX_RATE = float(os.getenv("DEFAULT_TAX_RATE", "18"))  # % GST agar document me na mile
COMPANY_NAME = os.getenv("COMPANY_NAME", "Your Company Pvt Ltd")
COMPANY_ADDRESS = os.getenv("COMPANY_ADDRESS", "Jaipur, Rajasthan, India")
COMPANY_GSTIN = os.getenv("COMPANY_GSTIN", "")

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")   # generated PDFs yahan save honge
LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- Behavior flags ---
# True -> missing required fields pe 422 error. False -> best-effort invoice bana dega.
STRICT_VALIDATION = os.getenv("STRICT_VALIDATION", "true").lower() == "true"
