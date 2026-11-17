# AURA — AI Voice Intelligence Platform

A real-time, full-duplex WebRTC Voice Assistant with a minimalist dark interface featuring reactive audio visualizers (Aura, Wave, Radial, Bar), light/dark modes, and multi-turn conversational memory. 

Powered by **Groq** for high-throughput LLM reasoning, **ElevenLabs + Edge-TTS** dual-engine speech synthesis, **Personal RAG Knowledge Base**, and **Real-Time Web Research MCP Engine**.

---

## 🏗️ Modular Architecture

The backend is organized into clean, maintainable domain packages:

```
backend/
├── core/                         # Core infrastructure
│   ├── config.py                 # Centralized configuration, paths, and settings
│   └── logging.py                # Structured logging, latency metrics, step profiler
│
├── modules/                      # Domain logic modules
│   ├── voice/                    # Real-time voice engine
│   │   ├── pipeline.py           # Groq streaming & dual-engine TTS synthesis
│   │   ├── session.py            # WebRTC call state, barge-in, turn management
│   │   └── media.py              # 16kHz PCMOutputTrack and PCMResampler
│   │
│   ├── rag/                      # Personal RAG Knowledge Base
│   │   ├── engine.py             # PDF extraction, chunking, hybrid vector search
│   │   └── tools.py              # RAG MCP tools (search, list, details)
│   │
│   └── web_research/             # Real-Time Web Research Engine
│       ├── engine.py             # Serper Google Search, Crawl4AI, Playwright fallback
│       ├── security.py           # SSRF protection, private IP blocking, URL validation
│       └── tools.py              # Web research MCP tools (search, scrape, fetch, compare)
│
├── routers/                      # Modular FastAPI APIRouters
│   ├── webrtc.py                 # /api/webrtc/offer, /ws/voice
│   ├── documents.py              # /api/documents/* (upload, search, list, delete)
│   ├── research.py               # /api/research/* (search, scrape, fetch, compare)
│   ├── chat.py                   # /api/chat (REST text queries with memory)
│   └── mcp.py                    # /api/mcp/* (MCP tool discovery & execution)
│
├── data/                         # Persistent storage
│   ├── knowledge_base/           # vector_store.json
│   └── uploads/                  # Ingested PDF files
│
├── main.py                       # Clean 85-line FastAPI application entrypoint
└── .env                          # API credentials (GROQ, ELEVENLABS, SERPER)
```

---

## 🚀 Getting Started

### 1. Environment Setup
Configure your API keys in `backend/.env`:
```env
GROQ_API_KEY=your_groq_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
SERPER_API_KEY=your_serper_api_key
```

### 2. Install Dependencies
```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m playwright install chromium
```

### 3. Run the Server
```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8001
```

Open your browser at:
👉 **`http://localhost:8001`**

---

## 🌟 Operating Modes (Unified Voice Stage)

1. **Voice Bot (General AI):**
   - Natural open-ended voice conversation with multi-turn memory.
   - Multilingual support: English, Hindi, and Hinglish.
   - Interactive audio visualizer modes (`Aura`, `Wave`, `Radial`, `Bar`).

2. **PDF Agent (Document Voice Q&A):**
   - Upload PDF files via the slide-in **Documents Drawer**.
   - Questions are strictly grounded in document pages with 100% factual accuracy.
   - Hybrid semantic search with cross-lingual keyword and synonym mapping.

3. **News Agent (Real-Time Web Research):**
   - Searches Google live via Serper API.
   - Dual-engine speech synthesis (ElevenLabs + Edge-TTS zero-cost fallback).
   - Click **Live Sources** to inspect verified article cards and outbound links.

---

## 📄 Complete Technical Documentation

A full 6-page comprehensive project report with architecture diagrams and API specs is available in:
- `AURA_Project_Documentation.pdf`
