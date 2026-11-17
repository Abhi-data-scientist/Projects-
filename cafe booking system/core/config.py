import os
from dotenv import load_dotenv
load_dotenv(override=True)


class Settings:
    # MySQL
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "voice_sql_assistant")

    # Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    # Whisper
    WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
    WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    # Piper TTS
    PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "models/en_US-lessac-medium.onnx")
    PIPER_EXECUTABLE = os.getenv("PIPER_EXECUTABLE", "piper")

    # Folders
    AUDIO_DIR = os.getenv("AUDIO_DIR", "audio")
    LOGS_DIR = os.getenv("LOGS_DIR", "logs")

    APP_NAME = "REGEX CAFE"
    MAX_SQL_ROWS = int(os.getenv("MAX_SQL_ROWS", "200"))

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() in {"1", "true", "yes"}
    REDIS_CONNECT_TIMEOUT = float(os.getenv("REDIS_CONNECT_TIMEOUT", "0.5"))
    SQL_CACHE_TTL_SECONDS = int(os.getenv("SQL_CACHE_TTL_SECONDS", "60"))
    GENERAL_CACHE_TTL_SECONDS = int(os.getenv("GENERAL_CACHE_TTL_SECONDS", "3600"))
    REDIS_RETRY_COOLDOWN_SECONDS = int(os.getenv("REDIS_RETRY_COOLDOWN_SECONDS", "60"))

    # Twilio WhatsApp (optional)
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")

    # Auth / Session
    SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "28800"))  # 8 h
    # External AI/audio services are opt-in so a network outage never delays
    # the booking conversation. Set either value to true when desired.
    ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() in {"1", "true", "yes"}
    ENABLE_TTS = os.getenv("ENABLE_TTS", "false").lower() in {"1", "true", "yes"}


settings = Settings()
os.makedirs(settings.AUDIO_DIR, exist_ok=True)
os.makedirs(settings.LOGS_DIR, exist_ok=True)
