import asyncio
import json
import os
from urllib.parse import urlencode

import websockets
from aiortc import MediaStreamTrack
from aiortc.mediastreams import MediaStreamError
from av import AudioFrame

from core.logging import logger
from modules.voice.media import PCMOutputTrack, PCMResampler


class WebRTCSession:
    """Own all provider, peer, and cancellation state for one WebRTC call."""

    def __init__(self, pipeline, peer_connection) -> None:
        self.pipeline = pipeline
        self.peer_connection = peer_connection
        self.output_track = PCMOutputTrack(on_drain=self._on_audio_drained)
        self.control_channel = None
        self.input_task: asyncio.Task | None = None
        self.response_task: asyncio.Task | None = None
        self.interrupt_requested = False
        self.turn_audio_active = False
        self.closed = False
        self._turn_generation = 0
        self.mode = "general"
        self.history: list[dict] = []
        peer_connection.addTrack(self.output_track)

    def set_control_channel(self, channel) -> None:
        self.control_channel = channel

    async def send_event(self, event: dict) -> None:
        channel = self.control_channel
        if channel is not None and channel.readyState == "open":
            channel.send(json.dumps(event))

    async def interrupt(self) -> None:
        """Cancel provider streams and discard queued audio for an interrupted turn."""
        if self.closed:
            return
        self.interrupt_requested = True
        self.turn_audio_active = False
        self._turn_generation += 1
        self.output_track.clear()
        task = self.response_task
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self.send_event({"type": "interrupted"})

    def handle_control_message(self, message: str) -> asyncio.Task | None:
        try:
            payload = json.loads(message)
        except (TypeError, json.JSONDecodeError):
            return None
        msg_type = payload.get("type")
        if msg_type == "interrupt":
            return asyncio.create_task(self.interrupt())
        elif msg_type == "set_mode":
            mode = payload.get("mode", "general")
            if mode in ("general", "rag", "web"):
                self.mode = mode
                logger.info("Session mode switched to: %s", mode)
        elif msg_type == "clear_history":
            self.history = []
            logger.info("Session history cleared")
        elif msg_type == "client_transcript":
            text = payload.get("text", "").strip()
            if text:
                return asyncio.create_task(self._handle_transcript(text))
        return None

    async def run_input_track(self, track: MediaStreamTrack) -> None:
        """Stream inbound browser audio to ElevenLabs Realtime STT."""
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            await self.send_event({"type": "error", "message": "ELEVENLABS_API_KEY is not configured."})
            return
        query = urlencode({
            "model_id": "scribe_v2_realtime",
            "audio_format": "pcm_16000",
            "sample_rate": "16000",
            "commit_strategy": "vad",
            "vad_silence_threshold_secs": "0.8",
            "min_speech_duration_ms": "200",
            "filter_background_audio": "true",
        })
        url = f"wss://api.elevenlabs.io/v1/speech-to-text/realtime?{query}"
        try:
            async with websockets.connect(
                url,
                additional_headers={"xi-api-key": api_key},
                ping_interval=20,
                max_size=2**20,
            ) as stt:
                await self.send_event({"type": "ready"})
                resampler = PCMResampler()

                async def forward_audio() -> None:
                    while not self.closed:
                        frame: AudioFrame = await track.recv()
                        for pcm in resampler.convert(frame):
                            if pcm:
                                await stt.send(json.dumps({
                                    "message_type": "input_audio_chunk",
                                    "audio_base_64": __import__("base64").b64encode(pcm).decode("ascii"),
                                }))

                async def read_transcripts() -> None:
                    async for raw in stt:
                        event = json.loads(raw)
                        event_type = event.get("message_type", "")
                        if event_type == "partial_transcript":
                            partial_text = (event.get("text") or "").strip()
                            # Immediate Barge-In: if user speaks while assistant is speaking, cut off assistant audio immediately!
                            active_response = self.response_task and not self.response_task.done()
                            if (active_response or self.turn_audio_active) and partial_text:
                                logger.info("User barge-in detected via partial transcript: '%s'. Cutting off assistant.", partial_text)
                                await self.interrupt()
                            await self.send_event({"type": "partial", "text": partial_text})
                        elif event_type == "committed_transcript":
                            await self._handle_transcript((event.get("text") or "").strip())
                        elif event_type.endswith("error") or event_type in {"rate_limited", "quota_exceeded", "resource_exhausted"}:
                            detail = event.get("error") or event.get("message") or event_type
                            logger.warning("realtime_stt_notice type=%s detail=%s. Activating client STT fallback.", event_type, detail)
                            await self.send_event({"type": "enable_client_stt"})

                workers = [asyncio.create_task(forward_audio()), asyncio.create_task(read_transcripts())]
                done, pending = await asyncio.wait(workers, return_when=asyncio.FIRST_COMPLETED)
                for worker in pending:
                    worker.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                for worker in done:
                    if not worker.cancelled() and worker.exception():
                        pass
        except asyncio.CancelledError:
            raise
        except MediaStreamError:
            logger.info("webrtc_input_track_ended")
        except Exception as exc:
            logger.warning("webrtc_stt_notice: %s. Activating client STT fallback.", exc)
            await self.send_event({"type": "enable_client_stt"})

    async def _handle_transcript(self, text: str) -> None:
        if not text or self.closed:
            return
        active_response = self.response_task and not self.response_task.done()
        if active_response or self.turn_audio_active:
            # Seamless Barge-in: user spoke a new query while assistant was talking or draining audio.
            # Immediately stop the previous turn and process the new question without dropping it!
            logger.info("Seamless barge-in: cancelling active turn for new query: %s", text)
            await self.interrupt()

        self.interrupt_requested = False
        self.turn_audio_active = True
        self._turn_generation += 1
        generation = self._turn_generation
        self.output_track.begin_turn(generation)
        await self.send_event({"type": "transcript", "text": text})
        await self.send_event({"type": "turn_start"})
        self.response_task = asyncio.create_task(self._run_response(text, generation))

    async def _run_response(self, text: str, generation: int) -> None:
        try:
            import inspect
            sig = inspect.signature(self.pipeline.stream_reply)
            kwargs = {}
            if "history" in sig.parameters:
                kwargs["history"] = self.history
            if "mode" in sig.parameters:
                kwargs["mode"] = self.mode

            full_reply = await self.pipeline.stream_reply(
                text,
                self.send_event,
                self.output_track.push_pcm,
                **kwargs,
            )
            if full_reply and generation == self._turn_generation:
                self.history.append({"role": "user", "content": text})
                self.history.append({"role": "assistant", "content": full_reply})
                if len(self.history) > 16:
                    self.history = self.history[-16:]
                await self.send_event({"type": "history_updated", "count": len(self.history) // 2})
            if generation == self._turn_generation:
                await self.output_track.mark_turn_complete()
        except asyncio.CancelledError:
            logger.info("webrtc_response_cancelled")
            raise
        except Exception as exc:
            logger.exception("webrtc_response_failed")
            if generation == self._turn_generation:
                await self.output_track.mark_turn_complete()
                await self.send_event({"type": "error", "message": f"Assistant response failed: {exc}"})

    async def _on_audio_drained(self, generation: int) -> None:
        if not self.closed:
            self.turn_audio_active = False
            await self.send_event({"type": "turn_end"})

    async def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        current = asyncio.current_task()
        tasks = [task for task in (self.input_task, self.response_task) if task and task is not current and not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.output_track.stop()
