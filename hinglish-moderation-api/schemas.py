from typing import Optional, Literal
from pydantic import BaseModel


class ModerateRequest(BaseModel):
    text: str
    user_id: str
    context: Optional[Literal["chat", "course_review", "comment"]] = "chat"


class ModerateResponse(BaseModel):
    is_flagged: bool
    category: Literal["clean", "profanity", "spam", "harassment", "other"]
    cleaned_text: str
    explanation: str
    source: Literal["cache", "ner", "pos_tagging", "gemini_llm"]
    confidence: Literal["high", "medium", "low"]
