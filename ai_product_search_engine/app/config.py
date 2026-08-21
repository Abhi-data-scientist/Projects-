import os

from dotenv import load_dotenv


# Load local development settings before reading configuration. Environment
# variables supplied by the host still take precedence over values in .env.
load_dotenv()

# MySQL connection settings. Override via environment variables if needed,
# or just edit the defaults below to match your local MySQL setup.
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "product_search_db"),
}

# How many ranked products to return from /search
TOP_N_RESULTS = int(os.getenv("TOP_N_RESULTS", 5))
