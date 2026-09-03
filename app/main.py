import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import settings
from core.database import check_connection
from core.db_init import setup_database
from services import booking_service, whisper_service, tts_service
from api.chat import router as chat_router
from api.seats import router as seats_router
from api.auth import router as auth_router
from api.bookings import router as bookings_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            Path(settings.LOGS_DIR) / "app.log",
            maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("main")

app = FastAPI(title=settings.APP_NAME)
BASE_DIR = Path(__file__).resolve().parent

app.mount("/audio", StaticFiles(directory=settings.AUDIO_DIR), name="audio")
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(seats_router)
app.include_router(bookings_router)

scheduler = AsyncIOScheduler()


@app.on_event("startup")
async def startup_event():
    logger.info("Starting %s...", settings.APP_NAME)
    setup_database()
    try:
        whisper_service.load_model()
    except Exception as e:
        logger.error("Whisper load failed: %s", e)
    scheduler.add_job(booking_service.expire_old_bookings, "interval", minutes=1)
    scheduler.start()
    logger.info("Startup complete.")


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown(wait=False)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "connected" if check_connection() else "disconnected",
        "whisper": "loaded" if whisper_service.is_loaded() else "not_loaded",
        "tts": "available" if tts_service.is_loaded() else "unavailable",
    }


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(BASE_DIR / "static" / "index.html")
