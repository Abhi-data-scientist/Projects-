"""
Single choke point for every LLM call in the system.

Keeping this in one file means:
- one place to swap the SDK / provider later
- one place to log token usage for cost tracking
- one place to enforce JSON-only output when an agent needs structured data
"""
import json
import logging

from groq import BadRequestError, Groq

from app.config import settings

logger = logging.getLogger("ai_ki_agency.groq")

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def call_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    heavy: bool = False,
    json_mode: bool = False,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    """
    Runs one chat completion and returns the raw text content.

    temperature is kept low by default (0.2) - this is a builder/reasoning
    pipeline, not a creative-writing one, and low temperature also tends to
    need fewer retries (= fewer wasted tokens = cheaper).
    """
    client = get_client()
    model = settings.groq_model_heavy if heavy else settings.groq_model_light
    token_limit = max_tokens or (settings.max_tokens_heavy if heavy else settings.max_tokens_light)

    kwargs: dict = dict(
        model=model,
        temperature=temperature,
        max_tokens=token_limit,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    completion = client.chat.completions.create(**kwargs)

    usage = getattr(completion, "usage", None)
    if usage:
        logger.info(
            "model=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s",
            model,
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.total_tokens,
        )

    return completion.choices[0].message.content or ""


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    *,
    heavy: bool = False,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> dict:
    """Convenience wrapper for agents that need structured JSON back.

    Some reasoning models can exhaust a small completion budget before they
    close the JSON object. Groq then returns ``json_validate_failed`` rather
    than a partial response, so retry once with a larger budget.
    """
    initial_limit = max_tokens or (
        settings.max_tokens_heavy if heavy else settings.max_tokens_light
    )
    try:
        raw = call_llm(
            system_prompt,
            user_prompt,
            heavy=heavy,
            json_mode=True,
            temperature=temperature,
            max_tokens=initial_limit,
        )
    except BadRequestError as exc:
        if "json_validate_failed" not in str(exc):
            raise

        retry_limit = max(initial_limit * 2, settings.max_tokens_json_retry)
        logger.warning(
            "JSON generation hit token limit with max_tokens=%s; retrying once with max_tokens=%s",
            initial_limit,
            retry_limit,
        )
        raw = call_llm(
            system_prompt,
            user_prompt,
            heavy=heavy,
            json_mode=True,
            temperature=temperature,
            max_tokens=retry_limit,
        )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Model did not return valid JSON, wrapping raw text")
        return {"raw": raw}
