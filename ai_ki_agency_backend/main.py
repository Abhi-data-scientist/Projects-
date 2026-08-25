import logging
import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.open_browser_on_start:
        # Run outside startup so Uvicorn can begin accepting requests first.
        threading.Timer(0.8, lambda: webbrowser.open_new("http://127.0.0.1:8000/")).start()
    yield


app = FastAPI(
    title="AI_KI_AGENCY Backend",
    description="Multi-agent pipeline: Requirement -> Architecture -> Tools -> Cost -> Preview -> Coding -> Bug Report -> Bug Fix",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Mount last so API and health routes remain available while all frontend
# assets (index.html, CSS, and JavaScript) are served from the same origin.
app.mount("/", StaticFiles(directory=Path(__file__).parent / "frontend", html=True), name="frontend")
