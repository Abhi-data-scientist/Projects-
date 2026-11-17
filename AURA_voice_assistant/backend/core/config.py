"""Core configuration and settings for Aura Voice Assistant."""

from pathlib import Path
import os
from dotenv import load_dotenv

# Base paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = BACKEND_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables
load_dotenv(BACKEND_DIR / ".env")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))

# Voice settings
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
FALLBACK_VOICE_EN = "en-IN-NeerjaNeural"
FALLBACK_VOICE_HI = "hi-IN-SwaraNeural"
