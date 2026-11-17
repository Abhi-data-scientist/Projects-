"""Aura Voice Assistant — Main Application Entrypoint.

Modular FastAPI architecture connecting:
- WebRTC Audio Streaming & Signaling
- Personal RAG Knowledge Base (Vector Search)
- Real-Time Web Research MCP Engine (Serper & Web Scraping)
- Streaming LLM & Dual-Engine Speech Synthesis
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.config import FRONTEND_DIR
from core.logging import logger, track_latency
from routers import documents, research, chat, webrtc, mcp
from routers.webrtc import active_webrtc_sessions


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Aura application startup complete.")
    yield
    logger.info("Shutting down active WebRTC sessions...")
    for peer, session in list(active_webrtc_sessions.items()):
        active_webrtc_sessions.pop(peer, None)
        await session.close()
        await peer.close()
    logger.info("Aura application shutdown complete.")


app = FastAPI(
    title="Aura Voice Assistant API",
    version="2.0.0",
    description="Next-Gen Real-Time Conversational Voice AI Platform",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files (Frontend assets)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Include Modular Routers
app.include_router(webrtc.router)
app.include_router(documents.router)
app.include_router(research.router)
app.include_router(chat.router)
app.include_router(mcp.router)


@app.get("/")
@track_latency
def root():
    """Serve single-page frontend application."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {
        "service": "Aura Voice Assistant API",
        "version": "2.0.0",
        "status": "running",
        "health": "/health",
    }


@app.get("/health")
@track_latency
def health() -> dict:
    """Service health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from core.config import HOST, PORT
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
