"""Router for text queries and conversational memory grounding."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from functools import lru_cache

from core.logging import logger, track_latency
from modules.voice import VoicePipeline
from routers.documents import knowledge_base
from routers.research import web_research_engine

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatQueryRequest(BaseModel):
    message: str
    mode: str = "general"
    history: list[dict] = []


@lru_cache(maxsize=1)
def get_pipeline() -> VoicePipeline:
    return VoicePipeline(knowledge_base=knowledge_base, web_engine=web_research_engine)


@router.post("")
@track_latency
async def chat_endpoint(request: ChatQueryRequest) -> dict:
    """Send text query with conversational memory and mode-specific grounding."""
    try:
        pipeline = get_pipeline()
        collected_tokens: list[str] = []

        async def capture_event(ev: dict) -> None:
            if ev.get("type") == "text":
                collected_tokens.append(ev.get("text", ""))

        answer = await pipeline.stream_reply(
            user_text=request.message,
            send_event=capture_event,
            audio_sink=None,
            history=request.history,
            mode=request.mode,
            synthesize_audio=False,
        )
        return {
            "status": "success",
            "reply": answer,
            "mode": request.mode,
        }
    except Exception as exc:
        logger.exception("chat_endpoint_failed message=%s", request.message)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
