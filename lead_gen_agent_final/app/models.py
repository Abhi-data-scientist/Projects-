"""
Pydantic schemas - user se aane wale requests aur
API se jaane wale responses ka structure define karta hai.
"""
from pydantic import BaseModel, Field
from typing import Optional


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="e.g. 'marketing agencies in Jaipur'")
    max_results: int = Field(default=20, ge=5, le=50)
    min_score: int = Field(default=0, ge=0, le=10)
    require_email: bool = False
    require_phone: bool = False
    exclude_domains: list[str] = Field(default_factory=list)


class LeadOut(BaseModel):
    id: int
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    source_url: str
    score: int
    email_verified: bool
    extraction_method: Optional[str] = None


class JobOut(BaseModel):
    id: str
    query: str
    status: str
    total_urls: int
    processed_urls: int
    leads_found: int
    created_at: str
    updated_at: str
    error: Optional[str] = None


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str
    message: str
