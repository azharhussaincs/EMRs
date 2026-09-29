# HIPAA Security & Audit Compliance Architecture

## Regulatory Foundation: HIPAA Security Rule (45 CFR Part 160 & Part 164)

### 1. §164.312(b) Audit Controls
* **Immutable Event Logging**: Every API interaction, EMR ingestion, risk prediction evaluation, and GenAI synthesis is recorded as an immutable `AuditEvent`.
* **Cryptographic Integrity Verification**: Each audit entry calculates a SHA-256 hash across event attributes (`event_id`, `event_type`, `timestamp`, `actor_id`, `action`, `status`). Any tampering with logs results in a hash mismatch error.
* **Separation of Concerns**: Audit logs never store unencrypted or raw Protected Health Information (PHI).

### 2. §164.312(a)(2)(iv) Encryption and Decryption
* **In-Transit**: All communications between browser clients, API gateways, and microservices mandate TLS 1.3 encryption.
* **At-Rest**: Future database volumes and model storage require AES-256 encryption.

### 3. De-identification & Pseudonymization Protocol (Safe Harbor §164.514)
* Direct identifiers (patient names, full street addresses, Social Security numbers, medical record numbers) are stripped at the ingestion perimeter.
* Internal services and ML/LLM pipelines communicate strictly with pseudonymous identifiers (`PT-xxxxxxxx`) and relative temporal indices (e.g. days since baseline observation).

### 4. Role-Based Access Control (RBAC) Readiness
* System architected for clinical roles:
  * `Attending Clinician`: Read/write assessments, sign-off on narrative rationales.
  * `Consulting Specialist`: In-depth biomarker exploration and simulation.
  * `Clinical Auditor`: Read-only access to HIPAA audit trails.
  * `System Operator`: Diagnostic probes and infrastructure telemetry.
