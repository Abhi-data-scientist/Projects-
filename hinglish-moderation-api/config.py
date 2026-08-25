import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "5"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

# Fuzzy-match threshold used by the POS-tagging fallback layer.
# Higher = stricter (fewer false positives), lower = catches more spelling variants.
POS_FUZZY_CUTOFF = float(os.getenv("POS_FUZZY_CUTOFF", "0.82"))
