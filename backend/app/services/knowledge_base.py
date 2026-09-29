from abc import ABC, abstractmethod
from typing import List
from app.core.config import ClinicalDomain
from app.schemas.knowledge import KnowledgeQueryRequest, ClinicalKnowledgeChunk


class BaseClinicalKnowledgeBase(ABC):
    """
    Abstract interface for Clinical Guideline & Ontology RAG vector stores.
    Supports pgvector, Qdrant, Chroma, and hybrid BM25 + dense neural retrieval.
    """

    @abstractmethod
    async def query_guidelines(
        self,
        request: KnowledgeQueryRequest,
    ) -> List[ClinicalKnowledgeChunk]:
        """Retrieve relevant clinical guideline chunks with evidence levels."""
        pass

    @abstractmethod
    async def index_guideline_chunk(
        self,
        chunk: ClinicalKnowledgeChunk,
    ) -> bool:
        """Add new validated guideline excerpt into knowledge store."""
        pass
