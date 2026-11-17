import asyncio
import base64
import os
import re
from pathlib import Path
from typing import Awaitable, Callable

from dotenv import load_dotenv
from elevenlabs.client import AsyncElevenLabs
from groq import AsyncGroq

from core.logging import logger, measure_step, track_latency
from modules.rag.engine import PersonalRAGKnowledgeBase
from modules.web_research.engine import WebResearchEngine

load_dotenv(Path(__file__).with_name(".env"))
SendEvent = Callable[[dict], Awaitable[None]]
AudioSink = Callable[[bytes], Awaitable[None]]


def is_web_research_query(text: str) -> bool:
    """Fast lexical heuristics to detect if user query warrants real-time web search."""
    low = text.lower().strip()
    triggers = [
        "search web", "search online", "search for", "google", "web search",
        "latest", "current", "today", "yesterday", "recent", "weather",
        "price of", "score", "news", "aaj ka", "aaj ki", "taza khabar",
        "online dekh", "online search", "net pe", "who won", "live update",
        "stock price", "release date", "what happened to"
    ]
    return any(t in low for t in triggers)


class VoicePipeline:
    """Cancellation-aware streamed Groq and ElevenLabs speech pipeline with RAG & Web Research grounding."""

    @track_latency
    def __init__(
        self,
        knowledge_base: PersonalRAGKnowledgeBase | None = None,
        web_engine: WebResearchEngine | None = None,
    ) -> None:
        eleven_key = os.getenv("ELEVENLABS_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        if not eleven_key or not groq_key:
            raise RuntimeError("ELEVENLABS_API_KEY and GROQ_API_KEY must be set in backend/.env")
        self.eleven = AsyncElevenLabs(api_key=eleven_key)
        self.groq = AsyncGroq(api_key=groq_key)
        self.kb = knowledge_base
        self.web = web_engine or WebResearchEngine()

    @track_latency
    async def stream_reply(
        self,
        user_text: str,
        send_event: SendEvent,
        audio_sink: AudioSink | None = None,
        history: list[dict] | None = None,
        mode: str = "general",
        synthesize_audio: bool = True,
    ) -> str:
        """Stream LLM tokens and synthesize completed phrases incrementally with Conversational Memory & Mode Grounding."""
        system_prompt = (
            "You are Aura, an intelligent, human-like voice assistant. "
            "Reply in the same language as the user (e.g., Hindi, Hinglish, English).\n"
            "Keep spoken responses conversational, crisp, natural, and within 1-3 clear sentences unless asked for code or deep explanation.\n"
            "You have conversational memory: use previous messages from the dialogue to understand pronouns and context."
        )

        # ---------------------------------------------------------------------
        # MODE 1: PDF Knowledge Base Mode ("rag")
        # ---------------------------------------------------------------------
        if mode == "rag":
            system_prompt = (
                "You are Aura's Document Knowledge Base Assistant. "
                "Your role is to answer questions strictly grounded in the user's uploaded PDF documents.\n"
                "Reply in the user's language (Hindi, Hinglish, or English).\n"
                "Be direct, confident, and provide exact details (like names, numbers, email, skills, dates) found in the documents."
            )
            if self.kb and self.kb.has_documents():
                matches = self.kb.search_documents(user_text, top_k=6, min_score=0.05)
                # If small document set (e.g. resumes, notes under 12 chunks), include all chunks for 100% accuracy
                if len(self.kb.chunks) <= 12:
                    all_chunks = self.kb.chunks
                    context = "\n\n---\n\n".join(
                        f"[Document: {m['filename']} | Page: {m['page']}]\n{m['text']}" for m in all_chunks
                    )
                elif matches:
                    context = "\n\n---\n\n".join(
                        f"[Document: {m['filename']} | Page: {m['page']}]\n{m['text']}" for m in matches
                    )
                else:
                    context = ""

                if context:
                    system_prompt += (
                        f"\n\nDocument Excerpts:\n{context}\n\n"
                        "DOCUMENT ANSWER RULES:\n"
                        "- Answer the question accurately using the document excerpts provided above.\n"
                        "- State facts directly (e.g. phone numbers, email, skills, experience, education, summaries).\n"
                        "- If the user asks in Hindi/Hinglish, reply naturally in Hinglish."
                    )
                else:
                    system_prompt += (
                        "\n\nNote: The user query was not found in the uploaded documents. "
                        "Politely inform the user that their query wasn't found in their uploaded PDFs."
                    )
            else:
                system_prompt += (
                    "\n\nNote: No documents have been uploaded yet in the Knowledge Base. "
                    "Politely remind the user to upload a PDF in this section to start asking questions about it."
                )

        # ---------------------------------------------------------------------
        # MODE 2: Web Research & Recent News Mode ("web")
        # ---------------------------------------------------------------------
        elif mode == "web":
            system_prompt = (
                "You are Aura's Real-Time Web Research & News Assistant. "
                "Your role is to provide up-to-date, verified, evidence-based answers using real-time web search.\n"
                "Reply in the user's language (Hindi, Hinglish, or English)."
            )
            if self.web:
                try:
                    await send_event({"type": "search_status", "text": "Searching live web..."})
                    search_res = await self.web.search_web(query=user_text, num_results=4)
                    results_list = search_res.get("results", [])
                    if results_list:
                        web_blocks = []
                        for r in results_list:
                            web_blocks.append(
                                f"Source: {r.get('source')} | Title: {r.get('title')}\nURL: {r.get('link')}\nSnippet: {r.get('snippet')}"
                            )
                        evidence_str = "\n\n---\n\n".join(web_blocks)
                        system_prompt += (
                            f"\n\nLive Web Search Results:\n{evidence_str}\n\n"
                            "RULES FOR WEB RESEARCH:\n"
                            "- Base your answer on these live search results.\n"
                            "- Cite the source publications naturally (e.g., 'According to [source]...').\n"
                            "- In markdown text, include URLs as markdown links [Source Name](url).\n"
                            "- Keep voice responses crisp (1-3 sentences)."
                        )
                except Exception as search_err:
                    logger.warning("web_mode_search_failed error=%s", search_err)
                    system_prompt += f"\n\nNote: Live web search encountered an issue ({search_err})."

        # ---------------------------------------------------------------------
        # MODE 3: General Voice Bot Mode ("general")
        # ---------------------------------------------------------------------
        else:
            # Fallback check if user in general chat explicitly asks about PDF or web
            is_doc_query = any(k in user_text.lower() for k in ["pdf", "document", "notes", "uploaded doc"])
            if is_doc_query and self.kb and self.kb.has_documents():
                matches = self.kb.search_documents(user_text, top_k=2, min_score=0.45)
                if matches and matches[0]["score"] >= 0.55:
                    context = "\n\n---\n\n".join(
                        f"[Document: {m['filename']} | Page: {m['page']}]\n{m['text']}" for m in matches
                    )
                    system_prompt += f"\n\nDocument Excerpts:\n{context}\n"
            elif self.web and is_web_research_query(user_text):
                try:
                    search_res = await self.web.search_web(query=user_text, num_results=2)
                    results_list = search_res.get("results", [])
                    if results_list:
                        web_blocks = [
                            f"Source: {r.get('source')} | Title: {r.get('title')}\nURL: {r.get('link')}\nSnippet: {r.get('snippet')}"
                            for r in results_list
                        ]
                        system_prompt += f"\n\nLive Web Search:\n" + "\n\n---\n\n".join(web_blocks) + "\n"
                except Exception:
                    pass

        # Construct conversation messages with multi-turn history buffer
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            # Keep up to last 10 messages (5 turns) for context
            for h in history[-10:]:
                role = h.get("role")
                content = h.get("content")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_text})

        response = await self.groq.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            max_tokens=300,
            stream=True,
        )
        pending = ""
        full_answer: list[str] = []
        try:
            async for item in response:
                token = item.choices[0].delta.content or ""
                if not token:
                    continue
                pending += token
                full_answer.append(token)
                while True:
                    match = re.search(r"(?<=[.!?।])\s+", pending)
                    if not match and len(pending) >= 220:
                        match = re.search(r"\s+", pending[160:])
                        if match:
                            boundary = 160 + match.end()
                            phrase, pending = pending[:boundary].strip(), pending[boundary:].lstrip()
                            if synthesize_audio:
                                await self._speak_phrase(phrase, send_event, audio_sink)
                            else:
                                await send_event({"type": "text", "text": phrase})
                            continue
                    if not match:
                        break
                    phrase, pending = pending[:match.end()].strip(), pending[match.end():].lstrip()
                    if phrase:
                        if synthesize_audio:
                            await self._speak_phrase(phrase, send_event, audio_sink)
                        else:
                            await send_event({"type": "text", "text": phrase})
            if pending.strip():
                if synthesize_audio:
                    await self._speak_phrase(pending.strip(), send_event, audio_sink)
                else:
                    await send_event({"type": "text", "text": pending.strip()})
            return "".join(full_answer).strip()
        finally:
            close = getattr(response, "aclose", None) or getattr(response, "close", None)
            if close:
                if asyncio.iscoroutinefunction(close):
                    await close()
                else:
                    res = close()
                    if asyncio.iscoroutine(res):
                        await res

    @track_latency
    async def _speak_phrase(
        self,
        phrase: str,
        send_event: SendEvent,
        audio_sink: AudioSink | None = None,
    ) -> None:
        await send_event({"type": "text", "text": phrase})
        # Clean markdown links [Title](url) -> Title and remove raw URLs and formatting
        spoken_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", phrase)
        spoken_text = re.sub(r"https?://\S+", "", spoken_text)
        spoken_text = re.sub(r"[*_`#~]", "", spoken_text)
        spoken_text = re.sub(r"\s+", " ", spoken_text).strip()
        if not spoken_text:
            return

        # Attempt ElevenLabs TTS first
        eleven_succeeded = False
        output_format = "pcm_16000" if audio_sink else "mp3_44100_128"
        try:
            with measure_step("text_to_speech_phrase_eleven"):
                audio_stream = self.eleven.text_to_speech.stream(
                    text=spoken_text,
                    voice_id="JBFqnCBsd6RMkjVDRZzb",
                    model_id="eleven_flash_v2_5",
                    output_format=output_format,
                )
                collected = bytearray()
                async for chunk in audio_stream:
                    if not chunk:
                        continue
                    if audio_sink:
                        await audio_sink(chunk)
                    else:
                        collected.extend(chunk)
                if collected and not audio_sink:
                    await send_event({"type": "audio", "audio_base64": base64.b64encode(collected).decode("ascii")})
                eleven_succeeded = True
        except Exception as eleven_err:
            logger.warning("elevenlabs_tts_unavailable error=%s. Falling back to Edge-TTS neural voice.", eleven_err)

        # Fallback to Edge-TTS (Infinite free neural voice, zero quota limits)
        if not eleven_succeeded:
            try:
                import io, av, edge_tts
                # Detect Hindi vs English characters
                is_hindi = any('\u0900' <= char <= '\u097F' for char in spoken_text)
                voice = "hi-IN-SwaraNeural" if is_hindi else "en-IN-NeerjaNeural"

                with measure_step("text_to_speech_phrase_edgetts"):
                    tts = edge_tts.Communicate(spoken_text, voice=voice)
                    mp3_data = bytearray()
                    async for chunk in tts.stream():
                        if chunk.get("type") == "audio" and chunk.get("data"):
                            mp3_data.extend(chunk["data"])

                    if mp3_data:
                        if audio_sink:
                            container = av.open(io.BytesIO(mp3_data), format="mp3")
                            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
                            for frame in container.decode(audio=0):
                                for out_frame in resampler.resample(frame):
                                    pcm = bytes(out_frame.planes[0])
                                    if pcm:
                                        await audio_sink(pcm)
                        else:
                            await send_event({"type": "audio", "audio_base64": base64.b64encode(mp3_data).decode("ascii")})
            except Exception as edge_err:
                logger.error("edge_tts_fallback_failed error=%s", edge_err)
