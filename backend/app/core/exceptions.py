from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class ClinicalPlatformError(Exception):
    """Base exception for all clinical platform errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EMRValidationError(ClinicalPlatformError):
    """Raised when incoming EMR or FHIR structure violates clinical validation constraints."""
    pass


class ClinicalDomainNotFoundError(ClinicalPlatformError):
    """Raised when an unsupported or unregistered clinical disease domain is requested."""
    pass


class ModelInferenceError(ClinicalPlatformError):
    """Raised when predictive risk engine or model pipeline fails execution."""
    pass


class GenAIGenerationError(ClinicalPlatformError):
    """Raised when Generative AI narrative generation or guideline citation fails."""
    pass


class AuditComplianceError(ClinicalPlatformError):
    """Raised when audit event recording or integrity validation fails."""
    pass
