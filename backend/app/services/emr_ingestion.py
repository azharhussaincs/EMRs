from abc import ABC, abstractmethod
from typing import Dict, Any
from app.schemas.emr import PatientEMRPayload, EMRIngestionResponse


class BaseEMRIngestionService(ABC):
    """
    Abstract interface for EMR ingestion adapters.
    Supports future HL7 v2, FHIR R4, OMOP CDM, and CSV batch pipeline connectors.
    """

    @abstractmethod
    async def validate_payload(self, payload: PatientEMRPayload) -> bool:
        """Validate syntactic and clinical semantic constraints of EMR payload."""
        pass

    @abstractmethod
    async def ingest_patient_record(self, payload: PatientEMRPayload) -> EMRIngestionResponse:
        """Process and register an EMR payload for clinical risk feature extraction."""
        pass

    @abstractmethod
    async def extract_domain_features(self, patient_id: str, domain_name: str) -> Dict[str, Any]:
        """Extract domain-relevant biomarker time-series from patient record."""
        pass
