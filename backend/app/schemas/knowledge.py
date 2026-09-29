from typing import List, Optional
from pydantic import BaseModel, Field
from app.core.config import ClinicalDomain


class ClinicalKnowledgeChunk(BaseModel):
    chunk_id: str
    domain: ClinicalDomain
    source_title: str
    organization: str
    year: int
    evidence_grade: str
    section: str
    content_text: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class KnowledgeQueryRequest(BaseModel):
    domain: ClinicalDomain
    query: str = Field(..., min_length=3, description="Clinical query or symptom/guideline text")
    top_k: int = Field(default=3, ge=1, le=10)


class KnowledgeQueryResponse(BaseModel):
    domain: ClinicalDomain
    query: str
    total_results: int
    chunks: List[ClinicalKnowledgeChunk]
    retrieval_latency_ms: float
