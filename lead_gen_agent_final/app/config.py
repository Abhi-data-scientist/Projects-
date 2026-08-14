"""
Central configuration. Sab settings yahin se aati hain,
taaki kahin bhi hardcoded values na ho.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./leads.db")

    # Crawling
    MAX_CONCURRENT_CRAWLS: int = int(os.getenv("MAX_CONCURRENT_CRAWLS", "5"))
    CRAWL_TIMEOUT_MS: int = int(os.getenv("CRAWL_TIMEOUT_MS", "15000"))

    # Discovery
    DEFAULT_MAX_RESULTS: int = 20
    DUCKDUCKGO_DELAY_SECONDS: float = 1.5

    # Skip these domains during crawling (social media, junk)
    EXCLUDED_DOMAINS: list[str] = [
        "facebook.com", "instagram.com", "twitter.com", "x.com",
        "youtube.com", "pinterest.com", "tiktok.com",
        "linkedin.com/pulse", "quora.com", "reddit.com",
    ]

    # Skip these file extensions
    EXCLUDED_EXTENSIONS: tuple = (".pdf", ".jpg", ".png", ".zip", ".doc", ".docx")

    # Scoring weights
    SCORE_EMAIL: int = 3
    SCORE_PHONE: int = 2
    SCORE_COMPANY_NAME: int = 2
    SCORE_VERIFIED_EMAIL: int = 3

    # Paths
    EXPORT_DIR: str = "./exports"
    LOG_DIR: str = "./logs"


settings = Settings()
