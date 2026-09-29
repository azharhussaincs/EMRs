import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import ClinicalPlatformError
from app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"Starting {settings.PROJECT_NAME} v{settings.PROJECT_VERSION} in {settings.ENVIRONMENT} mode."
    )
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="""
## Production-Grade Generative AI-Based Clinical Risk Assessment Platform

Clinical decision support system designed to ingest longitudinal Electronic Medical Records (EMRs) 
and evaluate calibrated risk trajectories across four core chronic disease areas:

1. **Type 2 Diabetes Mellitus & Complications** (ADA Standards of Care)
2. **Cardiovascular Disease (ASCVD & Heart Failure)** (ACC/AHA Prevention Guidelines)
3. **Chronic Kidney Disease (CKD Progression & ESRD)** (KDIGO Clinical Practice Guidelines)
4. **Oncology Early Detection & Malignancy Screening** (NCCN Detection Guidelines)

### Architectural Pillars:
* **Strict Clinical Typing & Ontologies**: LOINC, SNOMED-CT, ICD-10, RxNorm
* **Zero PHI Leakage & Immutable Audit Trail**: Adherence to HIPAA §164.312
* **Modular Engine Adapters**: Extensible ML estimators and Generative AI synthesizers
* **Guideline-Grounded Explanations**: Evidence citations for clinician trust
    """,
    openapi_tags=[
        {"name": "Health & Diagnostics", "description": "System readiness, uptime, and subsystem health checks"},
        {"name": "Clinical Domains", "description": "Disease areas, LOINC biomarker specifications, and guideline registries"},
        {"name": "EMR Ingestion & Validation", "description": "FHIR R4-aligned patient demographic, lab, condition, and medication ingestion"},
        {"name": "Clinical Risk Engine", "description": "Risk prediction interfaces, confidence intervals, and feature attributions"},
        {"name": "Generative AI Narrative", "description": "Audience-tailored clinical rationale grounded in medical consensus"},
        {"name": "Clinical Guidelines & RAG", "description": "Evidence retrieval and clinical guideline embeddings"},
        {"name": "HIPAA Compliance & Audit", "description": "Immutable audit events and access verification"},
    ],
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_and_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{process_time:.2f}"
    return response


@app.exception_handler(ClinicalPlatformError)
async def clinical_platform_exception_handler(request: Request, exc: ClinicalPlatformError):
    logger.error(f"Clinical domain exception: {exc.message} - Details: {exc.details}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_type": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )


# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health & Diagnostics"], summary="Root API Gateway Status")
async def root():
    return {
        "platform": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs",
        "api_v1_prefix": settings.API_V1_STR,
    }
