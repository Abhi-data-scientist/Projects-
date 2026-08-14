"""
Orchestrator: poori pipeline ko chalata hai end-to-end.
Discovery -> Crawl -> Extract -> (LLM fallback if needed) -> Validate -> Score -> Store

Ye function FastAPI endpoint se call hoga, aur progress_callback
se SSE ko live updates bhejega.
"""
import logging
from app.agents.discovery import discover_urls
from app.agents.crawler import crawl_urls
from app.agents.extractor import extract_data, needs_llm_fallback
from app.agents.fallback import extract_with_llm, parse_search_query
from app.agents.validator import validate_lead_email
from app.agents.scorer import process_lead
from app.database import update_job, insert_lead

logger = logging.getLogger(__name__)


async def run_pipeline(job_id: str, request: dict, progress_cb=None):
    """
    request: dict matching SearchRequest schema
      {query, max_results, min_score, require_email, require_phone, exclude_domains}

    progress_cb: async function(stage: str, detail: dict) - SSE ke liye
    """
    async def emit(stage: str, **detail):
        if progress_cb:
            await progress_cb(stage, detail)

    try:
        update_job(job_id, status="running")
        await emit("started", query=request["query"])

        # ---------- Step 1: Query parsing (1 Groq call) ----------
        await emit("parsing_query")
        parsed = parse_search_query(request["query"])
        search_query = parsed.get("search_query") or request["query"]
        logger.info(f"[{job_id}] Parsed query: {parsed}")

        # ---------- Step 2: Discovery ----------
        await emit("discovering")
        urls = discover_urls(
            search_query,
            max_results=request.get("max_results", 20),
            extra_exclude=request.get("exclude_domains", []),
        )
        update_job(job_id, total_urls=len(urls))
        await emit("discovered", total_urls=len(urls))

        if not urls:
            update_job(job_id, status="completed", leads_found=0)
            await emit("completed", leads_found=0, reason="no_urls_found")
            return

        # ---------- Step 3: Crawling ----------
        await emit("crawling", total=len(urls))

        def crawl_progress(done, total):
            logger.info(f"[{job_id}] Crawled {done}/{total}")

        crawl_results = await crawl_urls(urls, progress_callback=crawl_progress)
        update_job(job_id, processed_urls=len(crawl_results))
        await emit("crawled", processed=len(crawl_results))

        # ---------- Step 4-7: Extract -> Fallback -> Validate -> Score -> Store ----------
        await emit("extracting")
        leads_found = 0

        for i, page in enumerate(crawl_results):
            if not page["success"] or not page["html"]:
                continue

            extracted = extract_data(page["html"], page["url"])

            # LLM fallback sirf jab regex fail ho
            llm_data = {}
            if needs_llm_fallback(extracted):
                llm_data = extract_with_llm(extracted["text"], page["url"])

            email = (extracted["emails"][0] if extracted["emails"] else llm_data.get("email"))
            phone = (extracted["phones"][0] if extracted["phones"] else llm_data.get("phone"))
            company_name = extracted["company_name"] or llm_data.get("company_name")
            address = llm_data.get("address")

            # User filters (require_email / require_phone)
            if request.get("require_email") and not email:
                continue
            if request.get("require_phone") and not phone:
                continue

            # Validate email
            email_validation = validate_lead_email(email, check_dns=False) if email else {"is_valid": False, "verified": False}

            from urllib.parse import urlparse
            website = urlparse(page["url"]).netloc.replace("www.", "")

            raw_lead = {
                "company_name": company_name,
                "email": email if email_validation.get("is_valid") else None,
                "phone": phone,
                "website": website,
                "address": address,
                "source_url": page["url"],
                "email_verified": email_validation.get("verified", False),
                "extraction_method": "llm_fallback" if llm_data.get("llm_used") else "regex",
                "raw_text_snippet": extracted.get("text", ""),
            }

            # Dedupe + score
            processed = process_lead(raw_lead)
            if processed is None:
                continue  # duplicate, skip

            # Min score filter
            if processed["score"] < request.get("min_score", 0):
                continue

            insert_lead(job_id, processed)
            leads_found += 1

            await emit("lead_found", index=i + 1, total=len(crawl_results), leads_found=leads_found)

        # ---------- Done ----------
        update_job(job_id, status="completed", leads_found=leads_found)
        await emit("completed", leads_found=leads_found)
        logger.info(f"[{job_id}] Pipeline completed: {leads_found} leads found")

    except Exception as e:
        logger.exception(f"[{job_id}] Pipeline failed")
        update_job(job_id, status="failed", error=str(e))
        await emit("failed", error=str(e))
