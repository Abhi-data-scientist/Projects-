# Lead Gen AI Agent

Multi-agent pipeline jo natural language query leke web se leads (company name, email, phone) nikalta hai — 100% free stack, no paid APIs.

## Stack
- **Backend:** FastAPI
- **Discovery:** DuckDuckGo (`ddgs`) — free, unlimited
- **Crawling:** Playwright (async, JS-heavy sites bhi handle karta hai)
- **Extraction:** Trafilatura + Regex (no LLM needed for most pages)
- **Fallback:** Groq LLM (`llama-3.3-70b-versatile`) — sirf tab jab regex fail ho
- **Validation:** email-validator
- **Storage:** SQLite
- **Export:** CSV / JSON / Excel (pandas)
- **Frontend:** Plain HTML/CSS/JS with SSE live progress

---

## Setup (pehli baar)

### 1. Virtual environment activate karo
```bash
cd lead_gen_agent
python3 -m venv venv          # agar venv already nahi hai to
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows
```

### 2. Dependencies install karo
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Environment variables setup karo
```bash
cp .env.example .env
```
Phir `.env` file khol ke apni Groq API key daalo:
```
GROQ_API_KEY=your_actual_key_here
```
Key yahan se milegi (free): https://console.groq.com/keys

---

## Run karna

```bash
uvicorn app.main:app --reload
```

Browser mein khol: **http://127.0.0.1:8000**

- Search box mein query daalo — e.g. "marketing agencies in Jaipur"
- Live progress dikhega (discovering → crawling → extracting → done)
- Results table mein leads aayenge
- Export button se CSV/JSON/Excel download kar sakte ho

API docs (Swagger): **http://127.0.0.1:8000/docs**

---

## Project Structure
```
lead_gen_agent/
├── requirements.txt
├── .env.example              # copy to .env, apni Groq key daalo
├── leads.db                   # SQLite database (auto-create hoga)
├── app/
│   ├── main.py                 # FastAPI app, saare endpoints
│   ├── config.py               # saari settings ek jagah
│   ├── database.py             # SQLite CRUD functions
│   ├── models.py                # Pydantic request/response schemas
│   └── agents/
│       ├── discovery.py         # DuckDuckGo se URL fetch
│       ├── crawler.py           # Playwright async crawler
│       ├── extractor.py         # Trafilatura + regex extraction
│       ├── fallback.py          # Groq LLM (sirf fallback ke liye)
│       ├── validator.py         # email validation
│       ├── scorer.py            # dedupe + quality scoring
│       ├── export.py            # CSV/JSON/Excel export
│       └── orchestrator.py      # sab agents ko jodta hai
├── frontend/
│   └── index.html                # simple UI, SSE se live progress
├── exports/                      # exported files yahan save hote hain
└── logs/
```

---

## Kaise kaam karta hai (Architecture)

```
User query
   → Query Parser (Groq — 1 call)
   → Discovery (DuckDuckGo se URLs)
   → URL Filter (junk/social/PDF skip)
   → Crawler (Playwright, 5 parallel pages)
   → Extractor (Trafilatura + regex — no LLM)
        ↓ (agar regex fail ho tabhi)
   → Groq Fallback (LLM se extraction)
   → Validator (email format/deliverability)
   → Scorer (weighted score 0-10) + Dedupe check
   → SQLite storage
   → Export (CSV/JSON/Excel)
```

**Groq quota kaise bachta hai:** LLM sirf 2 jagah call hota hai — (1) query parsing mein ek baar, (2) jab kisi page pe regex se email/phone bilkul na mile tab fallback ke roop mein. Zyada tar pages regex se hi handle ho jate hain.

---

## API Endpoints (quick reference)

| Method | Endpoint | Kaam |
|---|---|---|
| POST | `/api/search` | Naya search job start karo |
| GET | `/api/progress/{job_id}` | SSE — live progress |
| GET | `/api/results/{job_id}` | Job ke final results |
| GET | `/api/jobs` | Saare jobs ki list |
| GET | `/api/jobs/{job_id}/status` | Ek job ka status |
| GET | `/api/leads` | Saare stored leads (filters ke saath) |
| DELETE | `/api/leads/{id}` | Ek lead delete karo |
| GET | `/api/export/{job_id}?format=csv` | Export (csv/json/xlsx) |

Search request body example:
```json
{
  "query": "marketing agencies in Jaipur",
  "max_results": 20,
  "min_score": 0,
  "require_email": false,
  "require_phone": false,
  "exclude_domains": []
}
```

---

## Common Issues

**"GROQ_API_KEY not set" error**
→ `.env` file bani hai check karo aur usme key sahi se daali hai.

**Playwright browser not found**
→ `playwright install chromium` dobara chalao.

**DuckDuckGo "No results found" ya rate limit**
→ Thoda wait karke retry karo. Bahut zyada consecutive searches se temporary block ho sakta hai — `app/config.py` mein `DUCKDUCKGO_DELAY_SECONDS` badha do agar zyada hota hai.

**Groq quota exceeded**
→ Free tier daily limit hai. Extractor zyada tar pages regex se hi handle karta hai, to fallback rate kam rakhne ki koshish karo (`app/agents/extractor.py` mein `needs_llm_fallback` logic check karo).

---

## Notes
- Ye project development/testing ke liye hai. Production mein deploy karne se pehle rate limiting, authentication, aur proper logging add karna recommended hai.
- Website scraping karte waqt respective site ke `robots.txt` aur terms of service respect karo.
- Bulk scraping se kisi site ka IP block ho sakta hai — crawl concurrency (`MAX_CONCURRENT_CRAWLS` in config.py) zyada mat badhao.
