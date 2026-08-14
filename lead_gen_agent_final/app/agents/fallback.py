"""
Fallback Agent: Groq LLM se contact info nikalta hai, LEKIN sirf tab
jab Extractor (regex+Trafilatura) kuch nahi nikal paya. Isse quota bachta hai.

Structured JSON output prompt use karta hai taaki parsing reliable rahe.
"""
import json
import logging
from groq import Groq
from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in .env file")
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


EXTRACTION_PROMPT = """You are a data extraction assistant. From the following website text, \
extract business contact information. Respond ONLY with valid JSON, no preamble, no markdown \
formatting, no backticks - just the raw JSON object.

Required JSON format:
{{
  "company_name": "string or null",
  "email": "string or null",
  "phone": "string or null",
  "address": "string or null"
}}

If a field cannot be found, use null. Do not make up information that isn't in the text.

Website text:
\"\"\"
{text}
\"\"\"
"""


def extract_with_llm(text: str, url: str = "", max_chars: int = 3000) -> dict:
    """
    Groq LLM se structured contact data extract karta hai.
    text truncate hota hai max_chars tak - taaki token usage kam rahe.
    """
    if not text or len(text.strip()) < 20:
        return {"company_name": None, "email": None, "phone": None, "address": None, "llm_used": False}

    truncated_text = text[:max_chars]

    try:
        client = get_client()
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "user", "content": EXTRACTION_PROMPT.format(text=truncated_text)},
            ],
            temperature=0.1,   # low temp - factual extraction, no creativity chahiye
            max_tokens=300,    # chhota output, quota bachane ke liye
        )
        raw = response.choices[0].message.content.strip()

        # Kabhi kabhi LLM markdown fences bhej deta hai, safety ke liye strip karo
        raw = raw.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(raw)
        parsed["llm_used"] = True
        logger.info(f"LLM fallback used for {url} - tokens: {response.usage.total_tokens}")
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON for {url}: {e}")
        return {"company_name": None, "email": None, "phone": None, "address": None, "llm_used": False}
    except Exception as e:
        logger.error(f"LLM fallback failed for {url}: {e}")
        return {"company_name": None, "email": None, "phone": None, "address": None, "llm_used": False}


def parse_search_query(user_query: str) -> dict:
    """
    User ki natural language query ko structured search terms mein convert karta hai.
    Ye pipeline ke START mein ek baar call hota hai (Query Parser Agent).
    Example: "marketing agencies in Jaipur" -> {"industry": "marketing agencies", "location": "Jaipur"}
    """
    prompt = f"""Extract the industry/business-type and location from this lead generation query. \
Respond ONLY with valid JSON, no markdown, no explanation.

Format:
{{"industry": "string", "location": "string or null", "search_query": "optimized google search string"}}

Query: "{user_query}"
"""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Query parsing failed: {e}")
        # Fallback: raw query hi use karo agar LLM fail ho
        return {"industry": user_query, "location": None, "search_query": user_query}
