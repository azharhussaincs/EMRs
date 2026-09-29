import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Union

from app.core.config import ClinicalDomain
from app.core.audit import AuditEvent, AuditEventType, audit_service
from app.schemas.explanation import AIExplanationContext, ASCVDExplanationContext
from app.schemas.narrative import (
    LLMStructuredNarrativePayload,
    ClinicalNarrativeExplanation,
)
from app.clinical.prompt_builder import (
    build_diabetes_narrative_prompt,
    build_cardiovascular_narrative_prompt,
)
from app.clinical.providers import BaseLLMProvider, get_llm_provider
from app.services.explanation_service import explanation_service


class ClinicalNarrativeValidationError(Exception):
    """Raised when LLM output violates structured schema or clinical safety boundaries."""
    pass


class ClinicalNarrativeService:
    """
    Production-grade narrative synthesis service coordinating prompt construction,
    LLM execution, strict structured output validation, and HIPAA audit logging.
    """

    # Prohibited clinical directive patterns (strictly non-prescriptive)
    TREATMENT_DIRECTIVE_PATTERN = re.compile(
        r"\b(prescribe|start\s+taking|increase\s+dose|decrease\s+dose|stop\s+taking|"
        r"administer\s+\d+|initiate\s+therapy\s+with|titrate\s+medication|start\s+insulin|"
        r"switch\s+to\s+metformin|prescribed\s+dosage)\b",
        re.IGNORECASE,
    )

    # Prohibited cardiovascular-specific medication/statin directives
    CARDIOVASCULAR_TREATMENT_PATTERN = re.compile(
        r"\b(initiate\s+statin|start\s+statin|start\s+taking\s+statin|prescribe\s+statin|prescribed\s+statin|"
        r"recommend\s+statin|recommended\s+statin|take\s+statin|taking\s+statin|"
        r"statin\s+therapy\s+indicated|statin\s+indicated|statin\s+therapy\s+recommended|"
        r"atorvastatin|rosuvastatin|simvastatin|pravastatin|"
        r"start\s+antihypertensive|prescribe\s+antihypertensive|initiate\s+antihypertensive|"
        r"amlodipine|lisinopril|beta\s*blocker|ace\s*inhibitor|"
        r"start\s+aspirin|prescribe\s+aspirin|initiate\s+aspirin)\b",
        re.IGNORECASE,
    )

    # Prohibited autonomous diagnostic claims
    DIAGNOSTIC_CLAIM_PATTERN = re.compile(
        r"\b(patient\s+is\s+diagnosed\s+with|we\s+diagnose|clinical\s+diagnosis\s+of|"
        r"diagnosed\s+as\s+having|definite\s+diagnosis\s+of)\b",
        re.IGNORECASE,
    )

    # Prohibited fabricated probability claims for uncalibrated models
    FABRICATED_PROBABILITY_PATTERN = re.compile(
        r"(\b\d{1,3}(\.\d+)?%\s*(risk|probability|chance|ascvd)|"
        r"\b(risk|probability|ascvd\s*score)\s*(of|is|:)?\s*\d{1,3}(\.\d+)?%|"
        r"\b10-year\s*(risk|probability|ascvd)\s*(of|is|:)?\s*\d{1,3}(\.\d+)?%)",
        re.IGNORECASE,
    )

    def validate_and_parse_llm_payload(
        self, raw_text: str, context: Union[AIExplanationContext, ASCVDExplanationContext]
    ) -> LLMStructuredNarrativePayload:
        """
        Parses and validates raw LLM output against strict clinical safety rules.
        Rejects malformed JSON, treatment recommendations, and fabricated probabilities.
        """
        # Strip potential markdown formatting if returned by model
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        try:
            data = json.loads(cleaned_text)
        except json.JSONDecodeError as exc:
            raise ClinicalNarrativeValidationError(
                f"LLM output could not be parsed as valid JSON: {str(exc)}"
            )

        try:
            payload = LLMStructuredNarrativePayload.model_validate(data)
        except Exception as exc:
            raise ClinicalNarrativeValidationError(
                f"LLM output does not match required structured schema: {str(exc)}"
            )

        full_content = (
            f"{payload.summary} {payload.observed_trajectory} "
            f"{payload.data_limitations} {payload.statistical_calibration_status}"
        )

        # Safety Check 1: Treatment or prescription recommendations prohibited
        if self.TREATMENT_DIRECTIVE_PATTERN.search(full_content):
            raise ClinicalNarrativeValidationError(
                "LLM output contained unauthorized clinical prescription or treatment directives."
            )

        # Safety Check 2: Cardiovascular-specific medication or statin directives prohibited
        if self.CARDIOVASCULAR_TREATMENT_PATTERN.search(full_content):
            raise ClinicalNarrativeValidationError(
                "LLM output contained unauthorized cardiovascular medication or statin therapy directives."
            )

        # Safety Check 3: Autonomous diagnostic claims prohibited
        if self.DIAGNOSTIC_CLAIM_PATTERN.search(full_content):
            raise ClinicalNarrativeValidationError(
                "LLM output contained unauthorized autonomous diagnostic claims."
            )

        # Safety Check 4: When estimator is uncalibrated, no numerical probability allowed
        if not context.is_statistically_calibrated:
            if self.FABRICATED_PROBABILITY_PATTERN.search(full_content):
                raise ClinicalNarrativeValidationError(
                    "LLM output claimed an unauthorized numerical probability for an uncalibrated estimator."
                )

        # Safety Check 5: Mandatory non-diagnostic disclaimer verification
        if "non-diagnostic" not in payload.disclaimer.lower() and "decision" not in payload.disclaimer.lower():
            raise ClinicalNarrativeValidationError(
                "LLM output failed to retain the mandatory non-diagnostic regulatory disclaimer."
            )

        return payload

    async def generate_diabetes_narrative(
        self,
        patient_id: str,
        actor_id: str = "clinician-portal",
        provider_override: Optional[BaseLLMProvider] = None,
    ) -> ClinicalNarrativeExplanation:
        """
        End-to-end synthesis workflow:
        1. Retrieve verified AIExplanationContext
        2. Construct controlled, grounded prompt
        3. Call configured LLM provider
        4. Validate structured output
        5. Record HIPAA audit event
        6. Return validated narrative explanation
        """
        # 1. Retrieve verified context (raises ValueError if patient not found)
        context = explanation_service.get_diabetes_context_for_patient(patient_id)

        # 2. Build controlled, grounded prompt
        system_instruction, user_prompt = build_diabetes_narrative_prompt(context)

        # 3. Obtain LLM provider instance
        provider = provider_override or get_llm_provider()

        request_id = str(uuid.uuid4())
        try:
            # 4. Invoke LLM provider
            raw_output = await provider.generate_structured_narrative(
                system_instruction=system_instruction, user_prompt=user_prompt
            )

            # 5. Strictly validate structured output
            parsed_payload = self.validate_and_parse_llm_payload(
                raw_text=raw_output, context=context
            )

            narrative = ClinicalNarrativeExplanation(
                narrative_id=f"narr-dm-{uuid.uuid4().hex[:12]}",
                context_id=context.context_id,
                patient_id=context.patient_id,
                assessment_id=context.assessment_id,
                domain=ClinicalDomain.DIABETES,
                summary=parsed_payload.summary,
                observed_trajectory=parsed_payload.observed_trajectory,
                data_limitations=parsed_payload.data_limitations,
                statistical_calibration_status=parsed_payload.statistical_calibration_status,
                disclaimer=parsed_payload.disclaimer,
                provider=provider.provider_name,
                model_name=provider.model_name,
                generated_at=datetime.now(timezone.utc),
            )

            # 6. Record successful HIPAA audit event
            audit_service.record_event(
                AuditEvent(
                    event_id=request_id,
                    event_type=AuditEventType.GENAI_INFERENCE,
                    actor_id=actor_id,
                    resource_id=patient_id,
                    action="generate_diabetes_narrative",
                    status="success",
                    metadata={
                        "narrative_id": narrative.narrative_id,
                        "context_id": context.context_id,
                        "assessment_id": context.assessment_id,
                        "estimator_version": context.estimator_version,
                        "provider": provider.provider_name,
                        "model_name": provider.model_name,
                    },
                )
            )

            return narrative

        except Exception as exc:
            # Record failed HIPAA audit event with failure metadata (no PHI)
            audit_service.record_event(
                AuditEvent(
                    event_id=request_id,
                    event_type=AuditEventType.GENAI_INFERENCE,
                    actor_id=actor_id,
                    resource_id=patient_id,
                    action="generate_diabetes_narrative",
                    status="failure",
                    metadata={
                        "context_id": context.context_id,
                        "assessment_id": context.assessment_id,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:200],
                        "provider": provider.provider_name,
                    },
                )
            )
            raise

    async def generate_cardiovascular_narrative(
        self,
        patient_id: str,
        actor_id: str = "clinician-portal",
        provider_override: Optional[BaseLLMProvider] = None,
    ) -> ClinicalNarrativeExplanation:
        """
        End-to-end synthesis workflow for Cardiovascular Disease:
        1. Retrieve verified ASCVDExplanationContext
        2. Construct controlled, grounded prompt
        3. Call configured LLM provider
        4. Validate structured output
        5. Record HIPAA audit event
        6. Return validated narrative explanation
        """
        # 1. Retrieve verified context (raises ValueError if patient not found)
        context = explanation_service.get_cardiovascular_context_for_patient(patient_id)

        # 2. Build controlled, grounded prompt
        system_instruction, user_prompt = build_cardiovascular_narrative_prompt(context)

        # 3. Obtain LLM provider instance
        provider = provider_override or get_llm_provider()

        request_id = str(uuid.uuid4())
        try:
            # 4. Invoke LLM provider
            raw_output = await provider.generate_structured_narrative(
                system_instruction=system_instruction, user_prompt=user_prompt
            )

            # 5. Strictly validate structured output
            parsed_payload = self.validate_and_parse_llm_payload(
                raw_text=raw_output, context=context
            )

            narrative = ClinicalNarrativeExplanation(
                narrative_id=f"narr-cvd-{uuid.uuid4().hex[:12]}",
                context_id=context.context_id,
                patient_id=context.patient_id,
                assessment_id=context.assessment_id,
                domain=ClinicalDomain.CARDIOVASCULAR,
                summary=parsed_payload.summary,
                observed_trajectory=parsed_payload.observed_trajectory,
                data_limitations=parsed_payload.data_limitations,
                statistical_calibration_status=parsed_payload.statistical_calibration_status,
                disclaimer=parsed_payload.disclaimer,
                provider=provider.provider_name,
                model_name=provider.model_name,
                generated_at=datetime.now(timezone.utc),
            )

            # 6. Record successful HIPAA audit event
            audit_service.record_event(
                AuditEvent(
                    event_id=request_id,
                    event_type=AuditEventType.GENAI_INFERENCE,
                    actor_id=actor_id,
                    resource_id=patient_id,
                    action="generate_cardiovascular_narrative",
                    status="success",
                    metadata={
                        "narrative_id": narrative.narrative_id,
                        "context_id": context.context_id,
                        "assessment_id": context.assessment_id,
                        "estimator_version": context.estimator_version,
                        "provider": provider.provider_name,
                        "model_name": provider.model_name,
                    },
                )
            )

            return narrative

        except Exception as exc:
            # Record failed HIPAA audit event with failure metadata (no PHI, no raw prompts)
            audit_service.record_event(
                AuditEvent(
                    event_id=request_id,
                    event_type=AuditEventType.GENAI_INFERENCE,
                    actor_id=actor_id,
                    resource_id=patient_id,
                    action="generate_cardiovascular_narrative",
                    status="failure",
                    metadata={
                        "context_id": context.context_id,
                        "assessment_id": context.assessment_id,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:200],
                        "provider": provider.provider_name,
                    },
                )
            )
            raise


narrative_service = ClinicalNarrativeService()
