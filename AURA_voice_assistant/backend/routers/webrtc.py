"""Router for WebRTC signaling and real-time audio streaming."""

import asyncio
import json
import os
from urllib.parse import urlencode

import websockets
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from aiortc import RTCPeerConnection, RTCSessionDescription

from core.logging import logger, track_latency
from modules.voice import WebRTCSession
from routers.chat import get_pipeline

router = APIRouter(tags=["webrtc"])

active_webrtc_sessions: dict[RTCPeerConnection, WebRTCSession] = {}


class WebRTCOffer(BaseModel):
    sdp: str
    type: str


@router.post("/api/webrtc/offer")
@track_latency
async def create_webrtc_answer(offer: WebRTCOffer) -> dict:
    """Accept a browser SDP offer and return a WebRTC SDP answer."""
    peer = RTCPeerConnection()
    session = None
    try:
        pipeline = get_pipeline()
        session = WebRTCSession(pipeline, peer)
        active_webrtc_sessions[peer] = session

        @peer.on("datachannel")
        def on_datachannel(channel) -> None:
            session.set_control_channel(channel)

            @channel.on("message")
            def on_message(message) -> None:
                if isinstance(message, str):
                    session.handle_control_message(message)

        @peer.on("track")
        def on_track(track) -> None:
            if track.kind == "audio":
                session.input_task = asyncio.create_task(session.run_input_track(track))

                @track.on("ended")
                async def on_ended() -> None:
                    if session.input_task and not session.input_task.done():
                        session.input_task.cancel()

        @peer.on("connectionstatechange")
        async def on_connection_state_change() -> None:
            if peer.connectionState in {"failed", "closed"}:
                active_webrtc_sessions.pop(peer, None)
                await session.close()
                if peer.connectionState != "closed":
                    await peer.close()

        await peer.setRemoteDescription(RTCSessionDescription(sdp=offer.sdp, type=offer.type))
        answer = await peer.createAnswer()
        await peer.setLocalDescription(answer)
        return {"sdp": peer.localDescription.sdp, "type": peer.localDescription.type}
    except Exception as exc:
        active_webrtc_sessions.pop(peer, None)
        if session:
            await session.close()
        await peer.close()
        logger.exception("webrtc_signaling_failed")
        raise HTTPException(status_code=500, detail=f"WebRTC signaling failed: {exc}") from exc


@router.websocket("/ws/voice")
@track_latency
async def voice_stream(client: WebSocket) -> None:
    await client.accept()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    query = urlencode({
        "model_id": "scribe_v2_realtime",
        "audio_format": "pcm_16000",
        "sample_rate": "16000",
        "commit_strategy": "vad",
        "vad_silence_threshold_secs": "1.0",
        "min_speech_duration_ms": "250",
        "filter_background_audio": "true",
    })
    upstream_url = f"wss://api.elevenlabs.io/v1/speech-to-text/realtime?{query}"
    send_lock = asyncio.Lock()
    turn_task: asyncio.Task | None = None

    async def send_event(payload: dict) -> None:
        async with send_lock:
            await client.send_json(payload)

    async def process_turn(text: str) -> None:
        try:
            await send_event({"type": "turn_start"})
            pipeline = get_pipeline()
            answer = await pipeline.stream_reply(text, send_event)
            await send_event({"type": "turn_end", "answer": answer})
        except asyncio.CancelledError:
            logger.info("stream_turn_cancelled")
            raise
        except Exception as exc:
            logger.exception("stream_turn_failed")
            await send_event({"type": "error", "message": str(exc)})

    try:
        pipeline = get_pipeline()
        async with websockets.connect(
            upstream_url,
            additional_headers={"xi-api-key": api_key},
            ping_interval=20,
            max_size=2**20,
        ) as stt:
            await send_event({"type": "ready"})

            async def send_audio_to_stt() -> None:
                nonlocal turn_task
                while True:
                    message = await client.receive()
                    if message["type"] == "websocket.disconnect":
                        return
                    audio = message.get("bytes")
                    if audio:
                        payload = {
                            "message_type": "input_audio_chunk",
                            "audio_base_64": __import__("base64").b64encode(audio).decode("ascii"),
                        }
                        await stt.send(json.dumps(payload))
                        continue
                    data = message.get("text")
                    if not data:
                        continue
                    command = json.loads(data)
                    if command.get("type") == "interrupt" and turn_task and not turn_task.done():
                        turn_task.cancel()

            async def receive_stt() -> None:
                nonlocal turn_task
                async for raw in stt:
                    event = json.loads(raw)
                    event_type = event.get("message_type")
                    if event_type == "partial_transcript":
                        await send_event({"type": "partial", "text": event.get("text", "")})
                    elif event_type == "committed_transcript":
                        text = (event.get("text") or "").strip()
                        if not text:
                            continue
                        if turn_task and not turn_task.done():
                            turn_task.cancel()
                        await send_event({"type": "transcript", "text": text})
                        turn_task = asyncio.create_task(process_turn(text))
                    elif event_type in {"error", "rate_limited", "scribe_error", "auth_error", "quota_exceeded", "input_error"}:
                        detail = event.get("error") or event.get("message") or event_type
                        await send_event({"type": "error", "message": str(detail)})
                        if event_type != "warning":
                            logger.error("realtime_stt_error type=%s detail=%s", event_type, detail)

            tasks = [asyncio.create_task(send_audio_to_stt()), asyncio.create_task(receive_stt())]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                if task.exception():
                    raise task.exception()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("voice_websocket_failed")
        try:
            await send_event({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        if turn_task and not turn_task.done():
            turn_task.cancel()
            await asyncio.gather(turn_task, return_exceptions=True)
        try:
            await client.close()
        except Exception:
            pass
