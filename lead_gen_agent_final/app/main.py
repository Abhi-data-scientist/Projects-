"""
FastAPI main application. Saare endpoints yahin define hain.
Run: uvicorn app.main:app --reload
"""
import asyncio
import json
import logging
import sys
import uuid
from contextlib import asynccontextmanager

# Windows par Playwright ko subprocess launch karne ke liye Proactor event loop
# chahiye - default Selector loop use karta hai jo subprocess support nahi karta.
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db, get_job, list_jobs, get_leads, delete_lead, create_job
from app.models import SearchRequest, JobCreatedResponse, JobOut, LeadOut
from app.agents.orchestrator import run_pipeline
from app.agents.export import export_leads

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# In-memory store of active job progress queues (SSE ke liye)
# job_id -> asyncio.Queue
_progress_queues: dict[str, asyncio.Queue] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(title="Lead Gen AI Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Health ----------

@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ---------- Search / Pipeline ----------

@app.post("/api/search", response_model=JobCreatedResponse)
async def start_search(request: SearchRequest):
    job_id = str(uuid.uuid4())
    create_job(job_id, request.query)
    _progress_queues[job_id] = asyncio.Queue()

    async def progress_cb(stage: str, detail: dict):
        queue = _progress_queues.get(job_id)
        if queue:
            await queue.put({"stage": stage, **detail})

    async def run_and_close():
        try:
            await run_pipeline(job_id, request.model_dump(), progress_cb=progress_cb)
        finally:
            queue = _progress_queues.get(job_id)
            if queue:
                await queue.put({"stage": "__end__"})

    # Background task - user ko turant job_id milta hai, pipeline background mein chalti hai
    asyncio.create_task(run_and_close())

    return JobCreatedResponse(job_id=job_id, status="pending", message="Search started")


@app.get("/api/progress/{job_id}")
async def progress_stream(job_id: str):
    """SSE endpoint - live progress updates."""
    if not get_job(job_id):
        raise HTTPException(404, "Job not found")

    async def event_generator():
        queue = _progress_queues.get(job_id)
        if not queue:
            # Job already finished ya queue expire ho gayi - final status bhej do
            job = get_job(job_id)
            yield f"data: {json.dumps({'stage': job['status']})}\n\n"
            return

        while True:
            event = await queue.get()
            if event.get("stage") == "__end__":
                yield f"data: {json.dumps({'stage': 'stream_closed'})}\n\n"
                _progress_queues.pop(job_id, None)
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/results/{job_id}")
async def get_results(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    leads = get_leads(job_id=job_id, page_size=1000)
    return {"job": job, "leads": leads}


# ---------- Jobs ----------

@app.get("/api/jobs")
async def api_list_jobs(limit: int = Query(default=50, ge=1, le=200)):
    return list_jobs(limit=limit)


@app.get("/api/jobs/{job_id}/status", response_model=JobOut)
async def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


# ---------- Leads ----------

@app.get("/api/leads")
async def api_get_leads(
    job_id: str = None,
    min_score: int = Query(default=0, ge=0, le=10),
    has_email: bool = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    return get_leads(job_id=job_id, min_score=min_score, has_email=has_email, page=page, page_size=page_size)


@app.delete("/api/leads/{lead_id}")
async def api_delete_lead(lead_id: int):
    delete_lead(lead_id)
    return {"deleted": lead_id}


# ---------- Export ----------

@app.get("/api/export/{job_id}")
async def api_export(job_id: str, format: str = Query(default="csv", pattern="^(csv|json|xlsx)$"), min_score: int = 0):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    try:
        path = export_leads(job_id, fmt=format, min_score=min_score)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return FileResponse(path, filename=f"leads_{job_id[:8]}.{format}")


# ---------- Frontend static files ----------
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")