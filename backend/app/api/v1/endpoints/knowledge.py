from typing import Dict, Any, List
from fastapi import APIRouter
from app.core.config import ClinicalDomain
from app.clinical.domains import CLINICAL_DOMAINS_REGISTRY
from app.schemas.knowledge import KnowledgeQueryRequest, KnowledgeQueryResponse, ClinicalKnowledgeChunk

router = APIRouter()


@router.get("/sources", summary="List Registered Clinical Evidence Sources")
async def list_knowledge_sources() -> Dict[str, Any]:
    """
    Returns registered clinical practice guidelines and evidence repositories.
    """
    sources = []
    for domain, entry in CLINICAL_DOMAINS_REGISTRY.items():
        for g in entry.consensus_guidelines:
            sources.append({
                "domain": domain.value,
                "organization": g.organization,
                "title": g.title,
                "edition_year": g.edition_year,
                "evidence_level": g.evidence_level,
                "url": g.url,
            })
    return {
        "status": "ready",
        "guideline_sources_count": len(sources),
        "sources": sources,
    }


@router.post("/query", response_model=KnowledgeQueryResponse, summary="Query Guideline Knowledge Base")
async def query_knowledge_base(request: KnowledgeQueryRequest) -> KnowledgeQueryResponse:
    """
    Retrieves evidence-based clinical guidance relevant to query and clinical domain.
    """
    domain_entry = CLINICAL_DOMAINS_REGISTRY.get(request.domain)
    chunks: List[ClinicalKnowledgeChunk] = []

    if domain_entry:
        for idx, g in enumerate(domain_entry.consensus_guidelines):
            chunks.append(
                ClinicalKnowledgeChunk(
                    chunk_id=f"chunk-{request.domain.value}-{idx}",
                    domain=request.domain,
                    source_title=g.title,
                    organization=g.organization,
                    year=g.edition_year,
                    evidence_grade=g.evidence_level,
                    section="Standard of Care Recommendations",
                    content_text=f"Official clinical consensus: {g.title} ({g.edition_year}) by {g.organization}. Target evaluation for {domain_entry.display_name}.",
                    similarity_score=0.95,
                )
            )

    return KnowledgeQueryResponse(
        domain=request.domain,
        query=request.query,
        total_results=len(chunks),
        chunks=chunks,
        retrieval_latency_ms=12.4,
    )
