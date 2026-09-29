from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    clinical_domains,
    emr,
    risk,
    genai,
    knowledge,
    evidence,
    audit,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health & Diagnostics"])
api_router.include_router(clinical_domains.router, prefix="/clinical/domains", tags=["Clinical Domains"])
api_router.include_router(emr.router, prefix="/emr", tags=["EMR Ingestion & Validation"])
api_router.include_router(risk.router, prefix="/risk", tags=["Clinical Risk Engine"])
api_router.include_router(genai.router, prefix="/genai", tags=["Generative AI Narrative"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["Clinical Guidelines & RAG"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["Clinical Evidence & Guidelines"])
api_router.include_router(audit.router, prefix="/audit", tags=["HIPAA Compliance & Audit"])
