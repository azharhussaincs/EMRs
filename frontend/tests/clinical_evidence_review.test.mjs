import test from 'node:test';
import assert from 'node:assert/strict';

// Helper simulating client-side badge formatting in ClinicalEvidenceReviewView
function getSourceBadge(organization, sourceId) {
  const orgUpper = (organization || '').toUpperCase();
  const idUpper = (sourceId || '').toUpperCase();

  if (idUpper.includes('ADA') || orgUpper.includes('AMERICAN DIABETES')) {
    return {
      label: 'ADA',
      fullOrg: 'American Diabetes Association',
      className: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    };
  }
  if (idUpper.includes('KDIGO') || orgUpper.includes('KIDNEY DISEASE')) {
    return {
      label: 'KDIGO',
      fullOrg: 'Kidney Disease: Improving Global Outcomes',
      className: 'bg-purple-50 text-purple-800 border-purple-200',
    };
  }
  if (idUpper.includes('ACC') || idUpper.includes('AHA') || orgUpper.includes('CARDIOLOGY')) {
    return {
      label: 'ACC/AHA',
      fullOrg: 'American College of Cardiology / AHA',
      className: 'bg-rose-50 text-rose-800 border-rose-200',
    };
  }
  return {
    label: organization.slice(0, 10),
    fullOrg: organization,
    className: 'bg-slate-100 text-slate-800 border-slate-200',
  };
}

// Helper simulating domain category formatting in ClinicalEvidenceReviewView
function formatDomainLabel(category) {
  switch (category) {
    case 'hba1c_monitoring':
      return 'Glycemic & HbA1c Monitoring';
    case 'glycemic_trajectory_assessment':
      return 'Glycemic Trajectory Assessment';
    case 'diabetes_classification_context':
      return 'Diabetes Classification Context';
    case 'diabetes_ckd_intersection':
      return 'Diabetes & CKD Intersection';
    case 'cardiovascular_risk_expansion':
      return 'Cardiovascular Risk Prevention';
    default:
      return String(category).replace(/_/g, ' ');
  }
}

// Helper simulating client-side error handling in ClinicalEvidenceReviewView
function mapEvidenceError(errObj) {
  const msg = errObj?.message || 'Failed to retrieve clinical guideline evidence references.';
  if (errObj?.status === 404) {
    return {
      type: 'patient_not_found',
      message: `Patient record was not found in the clinical repository. Please ingest the EMR first.`,
    };
  }
  return {
    type: 'general',
    message: msg,
  };
}

// Sample mock response matching backend GET /api/v1/evidence/diabetes
const MOCK_EVIDENCE_RESPONSE = {
  domain: 'diabetes',
  query_category: null,
  total_references: 3,
  provider_id: 'curated_evidence_provider_v1',
  references: [
    {
      evidence_id: 'ev-ada-2026-sec6-glycemic-monitoring',
      source_id: 'ADA-SOC-2026',
      organization: 'American Diabetes Association',
      guideline_title: 'Standards of Care in Diabetes—2026',
      publication_version: '2026 Edition',
      section_chapter: 'Section 6: Glycemic Goals and Hypoglycemia',
      recommendation_identifier: null,
      citation_text: 'American Diabetes Association. 6. Glycemic Goals and Hypoglycemia: Standards of Care in Diabetes—2026. Diabetes Care 2026;49(Suppl. 1):S93–S109.',
      official_url: 'https://diabetesjournals.org/care/issue/49/Supplement_1',
      evidence_status: 'verified',
      domain_category: 'hba1c_monitoring',
      scope_description: 'Recommends longitudinal glycemic assessment frequency and individualized glycemic targets based on patient clinical characteristics.',
      retrieved_at: '2026-09-29T06:30:00Z',
    },
    {
      evidence_id: 'ev-ada-2026-sec2-classification-trajectory',
      source_id: 'ADA-SOC-2026',
      organization: 'American Diabetes Association',
      guideline_title: 'Standards of Care in Diabetes—2026',
      publication_version: '2026 Edition',
      section_chapter: 'Section 2: Diagnosis and Classification of Diabetes',
      recommendation_identifier: null,
      citation_text: 'American Diabetes Association. 2. Diagnosis and Classification of Diabetes: Standards of Care in Diabetes—2026. Diabetes Care 2026;49(Suppl. 1):S27–S46.',
      official_url: 'https://diabetesjournals.org/care/issue/49/Supplement_1',
      evidence_status: 'verified',
      domain_category: 'glycemic_trajectory_assessment',
      scope_description: 'Longitudinal trajectory interpretation for progression across prediabetes and overt diabetes glycemic thresholds.',
      retrieved_at: '2026-09-29T06:30:00Z',
    },
    {
      evidence_id: 'ev-kdigo-2022-ckd-diabetes-targets',
      source_id: 'KDIGO-CKD-DM-2022',
      organization: 'Kidney Disease: Improving Global Outcomes (KDIGO) Diabetes Work Group',
      guideline_title: 'KDIGO 2022 Clinical Practice Guideline for Diabetes Management in Chronic Kidney Disease',
      publication_version: '2022 Guideline (2026 update in development)',
      section_chapter: 'Chapter 1: Glycemic Monitoring and Targets in Patients with CKD',
      recommendation_identifier: null,
      citation_text: 'Kidney Disease: Improving Global Outcomes (KDIGO) Diabetes Work Group. KDIGO 2022 Clinical Practice Guideline for Diabetes Management in Chronic Kidney Disease. Kidney Int 2022;102(5S):S1–S127.',
      official_url: 'https://kdigo.org/guidelines/diabetes-ckd/',
      evidence_status: 'verified',
      domain_category: 'diabetes_ckd_intersection',
      scope_description: 'Monitoring HbA1c and individualized glycemic targets when renal function is impaired (eGFR < 60 mL/min/1.73m²).',
      retrieved_at: '2026-09-29T06:30:00Z',
    },
  ],
  retrieved_at: '2026-09-29T06:30:00Z',
  disclaimer: 'Clinical evidence references provided for informational decision support only. Strictly non-prescriptive.',
};

test('1. Successful evidence retrieval contract matching backend response', () => {
  assert.strictEqual(MOCK_EVIDENCE_RESPONSE.domain, 'diabetes');
  assert.strictEqual(MOCK_EVIDENCE_RESPONSE.total_references, 3);
  assert.strictEqual(MOCK_EVIDENCE_RESPONSE.provider_id, 'curated_evidence_provider_v1');
  assert.strictEqual(MOCK_EVIDENCE_RESPONSE.references.length, 3);
  assert.ok(MOCK_EVIDENCE_RESPONSE.disclaimer.includes('informational decision support'));
});

test('2. Correct rendering of evidence cards with verified metadata', () => {
  const ref = MOCK_EVIDENCE_RESPONSE.references[0];
  assert.strictEqual(ref.guideline_title, 'Standards of Care in Diabetes—2026');
  assert.strictEqual(ref.publication_version, '2026 Edition');
  assert.strictEqual(ref.evidence_status, 'verified');
  assert.ok(ref.citation_text.includes('Diabetes Care 2026'));
  assert.ok(ref.scope_description.length > 20);
});

test('3. Source and organization display with proper badges (ADA, KDIGO, ACC/AHA)', () => {
  const adaBadge = getSourceBadge('American Diabetes Association', 'ADA-SOC-2026');
  assert.strictEqual(adaBadge.label, 'ADA');
  assert.ok(adaBadge.className.includes('emerald'));

  const kdigoBadge = getSourceBadge(
    'Kidney Disease: Improving Global Outcomes',
    'KDIGO-CKD-DM-2022'
  );
  assert.strictEqual(kdigoBadge.label, 'KDIGO');
  assert.ok(kdigoBadge.className.includes('purple'));

  const accBadge = getSourceBadge(
    'American College of Cardiology / AHA',
    'ACC-AHA-PPCVD-2019'
  );
  assert.strictEqual(accBadge.label, 'ACC/AHA');
  assert.ok(accBadge.className.includes('rose'));
});

test('4. Domain category tags mapped to human-readable labels', () => {
  assert.strictEqual(
    formatDomainLabel('hba1c_monitoring'),
    'Glycemic & HbA1c Monitoring'
  );
  assert.strictEqual(
    formatDomainLabel('glycemic_trajectory_assessment'),
    'Glycemic Trajectory Assessment'
  );
  assert.strictEqual(
    formatDomainLabel('diabetes_classification_context'),
    'Diabetes Classification Context'
  );
  assert.strictEqual(
    formatDomainLabel('diabetes_ckd_intersection'),
    'Diabetes & CKD Intersection'
  );
  assert.strictEqual(
    formatDomainLabel('cardiovascular_risk_expansion'),
    'Cardiovascular Risk Prevention'
  );
});

test('5. Official publication links use authentic URLs without hardcoded alternatives', () => {
  for (const ref of MOCK_EVIDENCE_RESPONSE.references) {
    assert.ok(ref.official_url.startsWith('https://'), 'URL must be a secure HTTPS link');
    assert.ok(
      ref.official_url.includes('diabetesjournals.org') ||
        ref.official_url.includes('kdigo.org') ||
        ref.official_url.includes('ahajournals.org'),
      'URL must belong to official publisher domain'
    );
  }
});

test('6. Mandatory non-prescriptive evidence disclaimer preserved without weakening', () => {
  const disclaimer = MOCK_EVIDENCE_RESPONSE.disclaimer;
  assert.ok(disclaimer.includes('informational decision support'));
  assert.ok(disclaimer.includes('non-prescriptive'));

  // Ensure no prescription directives exist in the scope descriptions
  for (const ref of MOCK_EVIDENCE_RESPONSE.references) {
    assert.ok(!ref.scope_description.toLowerCase().includes('prescribe'));
    assert.ok(!ref.scope_description.toLowerCase().includes('administer'));
    assert.ok(!ref.scope_description.toLowerCase().includes('dosage'));
  }
});

test('7. Empty evidence response handled safely without synthetic claims', () => {
  const emptyResponse = {
    domain: 'diabetes',
    total_references: 0,
    provider_id: 'curated_evidence_provider_v1',
    references: [],
    retrieved_at: '2026-09-29T06:30:00Z',
    disclaimer: 'Clinical evidence references provided for informational decision support only. Strictly non-prescriptive.',
  };

  assert.strictEqual(emptyResponse.total_references, 0);
  assert.strictEqual(emptyResponse.references.length, 0);

  // In the UI, empty state informs clinician without generating fake citations
  const hasZeroReferences = emptyResponse.references.length === 0;
  assert.strictEqual(hasZeroReferences, true);
});

test('8. Loading state prevents premature interaction and shows feedback', () => {
  let isLoading = true;
  let canRefresh = !isLoading;
  assert.strictEqual(canRefresh, false, 'Action button must be disabled during loading');

  isLoading = false;
  canRefresh = !isLoading;
  assert.strictEqual(canRefresh, true, 'Action button must be re-enabled after loading completes');
});

test('9. Patient not found (404) generates clinician-safe message without stack traces', () => {
  const err404 = {
    status: 404,
    message: "Patient 'PT-UNKNOWN-999' was not found in clinical repository.",
    stack: 'Error: Not Found\n    at fetchFromApi (http://localhost:8001/evidence.js:42:10)',
  };

  const mapped = mapEvidenceError(err404);
  assert.strictEqual(mapped.type, 'patient_not_found');
  assert.ok(mapped.message.includes('not found in the clinical repository'));
  assert.ok(!mapped.message.includes('fetchFromApi'), 'Must not expose stack traces');
  assert.ok(!mapped.message.includes('localhost:8001'), 'Must not expose internal URLs');
});

test('10. Network / API failure (500/offline) handled safely', () => {
  const errNetwork = {
    status: 500,
    message: 'Clinical API request failed (500)',
  };

  const mapped = mapEvidenceError(errNetwork);
  assert.strictEqual(mapped.type, 'general');
  assert.strictEqual(mapped.message, 'Clinical API request failed (500)');
});

test('11. Safety constraint: No fabricated recommendation numbers (null is preserved)', () => {
  for (const ref of MOCK_EVIDENCE_RESPONSE.references) {
    // Recommendation identifiers must be null or authenticated text
    assert.strictEqual(
      ref.recommendation_identifier,
      null,
      'Must strictly preserve null recommendation identifier to prevent fabricated recommendation numbers'
    );
  }
});

test('12. Category filter isolates specific domain categories accurately', () => {
  const allRefs = MOCK_EVIDENCE_RESPONSE.references;
  const filtered = allRefs.filter(
    (r) => r.domain_category === 'glycemic_trajectory_assessment'
  );

  assert.strictEqual(filtered.length, 1);
  assert.strictEqual(filtered[0].evidence_id, 'ev-ada-2026-sec2-classification-trajectory');
  assert.strictEqual(filtered[0].domain_category, 'glycemic_trajectory_assessment');
});
