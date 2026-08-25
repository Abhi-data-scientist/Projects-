# AI KI Agency

A FastAPI backend and chatbot-style frontend for manually operating a
multi-agent web-development workflow. Submit a query, then run each agent in
order and inspect its output before continuing.

## Workflow

```
Requirement -> Architecture -> Tools -> Cost -> Preview -> Coding
-> Bug Report -> Bug Fix -> Package
```

The Package stage creates a ZIP containing the final bug-fixed generated code.
Preview, Bug Report, and Package do not make LLM calls.

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add `GROQ_API_KEY` to `.env`, then run the backend:

```bash
uvicorn main:app --reload --port 8000
```

The frontend is served by the backend at `http://127.0.0.1:8000/` and opens
automatically when the server starts. Set `OPEN_BROWSER_ON_START=false` in
`.env` to disable auto-opening.

## API: exactly two endpoints

### `GET /health`

Health check response:

```json
{"status": "ok"}
```

### `POST /api/pipeline`

The single pipeline endpoint supports two actions.

Start a new query session:

```json
{
  "action": "start",
  "query": "Build a search bar for my website",
  "tech_hint": "plain HTML/CSS/JavaScript"
}
```

Run one agent after the previous agent succeeds:

```json
{
  "action": "run_agent",
  "session_id": "session-id-returned-by-start",
  "agent": "requirement"
}
```

Valid `agent` values are: `requirement`, `architecture`, `tools`, `cost`,
`preview`, `coding`, `bug_report`, `bug_fix`, and `package`. An out-of-order
request returns `409 Conflict`.

## Frontend

Keep the backend running on port 8000 and open `http://127.0.0.1:8000/` if the
browser did not open automatically. The frontend provides a chat interface and
left-side controls for running each agent one at a time; every agent result
appears in the conversation.

`ALLOWED_ORIGINS` in `.env` controls permitted frontend origins. The default
already includes the Live Server origin above.
