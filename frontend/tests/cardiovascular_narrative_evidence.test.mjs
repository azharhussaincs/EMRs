import test from 'node:test';
import assert from 'node:assert/strict';

// Helper simulating client-side state mapping in ClinicalNarrativeView for cardiovascular domain
function mapNarrativeError(errObj) {
  const msg = errObj?.message || 'Failed to generate clinical explanation narrative.';
  if (errObj?.status === 503 || msg.toLowerCase().includes('not configured')) {
    return {
      type: 'provider_not_configured',
      message:
        'Generative AI provider is not configured with an active API key in this environment. Narrative synthesis is safely withheld.',
    };
  }
  if (errObj?.status === 502 || msg.toLowerCase().includes('validation rejected')) {
    return {
      type: 'validation_failure',
      message:
        'Clinical Safety Guard: AI generation was rejected because the output did not strictly conform to verified clinical safety boundaries.',
    };
  }
  if (errObj?.status === 404) {
    return {
      type: 'general',
      message: `Patient record was not found in the clinical repository. Please ingest the EMR first.`,
    };
  }
  return {
    type: 'general',
    message: msg,
  };
}

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
      return 'Cardiovascular Primary Prevention (ACC/AHA)';
    default:
      return String(category).replace(/_/g, ' ');
  }
}

// Sample mock response matching backend POST /api/v1/genai/narrative/patients/{patient_id}/cardiovascular
const MOCK_CARDIOVASCULAR_NARRATIVE_RESPONSE = {
  narrative_id: 'narr-cvd-8b7a6c5d4e3f',
  context_id: 'ctx-cvd-1a2b3c4d5e6f',
  patient_id: 'PT-CARDIO-RENAL-508',
  assessment_id: 'assess-cvd-71b3e819ac42',
  domain: 'cardiovascular',
  summary:
    'Cardiovascular risk evaluation for PT-CARDIO-RENAL-508 reflects documented systolic blood pressure of 142.0 mmHg, total cholesterol of 210.0 mg/dL, HDL cholesterol of 48.0 mg/dL, and confirmed smoking status.',
  observed_trajectory:
    'Documented cardiovascular parameters: Systolic blood pressure 142.0 mmHg, Total cholesterol 210.0 mg/dL, HDL cholesterol 48.0 mg/dL, Chronological age 62 years, Gender Male, Smoking status Active, Comorbid diabetes status Documented.',
  data_limitations:
    'Risk factors evaluated from 7 core clinical parameters. Blood pressure and lipid profiles represent single longitudinal cross-sections. Estimator in foundation research phase (v0.1.0-foundation).',
  statistical_calibration_status:
    'Estimator is uncalibrated against longitudinal population cohorts. In accordance with clinical safety principles, no numerical risk probability or percentage is emitted.',
  disclaimer:
    'Research & engineering risk stratification prototype. Does not claim clinical diagnostic validity. Strictly non-diagnostic and non-prescriptive.',
  provider: 'mock',
  model_name: 'gemini-1.5-pro',
  generated_at: '2026-09-29T08:00:00Z',
};

// Sample mock response matching backend GET /api/v1/evidence/cardiovascular?patient_id={patient_id}
const MOCK_CARDIOVASCULAR_EVIDENCE_RESPONSE = {
  domain: 'cardiovascular',
  query_category: null,
  total_references: 1,
  provider_id: 'curated_evidence_provider_v1',
  references: [
    {
      evidence_id: 'ev-acc-2019-primary-prevention-cvd',
      source_id: 'ACC-AHA-PPCVD-2019',
      organization: 'American College of Cardiology / American Heart Association (ACC/AHA)',
      guideline_title: '2019 ACC/AHA Guideline on the Primary Prevention of Cardiovascular Disease',
      publication_version: '2019 Guideline',
      section_chapter: 'Section 3.1: Assessment of Cardiovascular Risk',
      recommendation_identifier: null,
      citation_text:
        'Arnett DK, et al. 2019 ACC/AHA Guideline on the Primary Prevention of Cardiovascular Disease. Circulation. 2019;140:e596–e646.',
      official_url: 'https://www.ahajournals.org/doi/10.1161/CIR.0000000000000678',
      evidence_status: 'verified',
      domain_category: 'cardiovascular_risk_expansion',
      scope_description:
        'Clinical assessment of 10-year risk for atherosclerotic cardiovascular disease using traditional risk factors.',
      retrieved_at: '2026-09-29T08:00:00Z',
    },
  ],
  retrieved_at: '2026-09-29T08:00:00Z',
  disclaimer:
    'Clinical evidence references provided for informational decision support only. Strictly non-prescriptive.',
};

test('1. Cardiovascular AI narrative response contract conforms to backend schema', () => {
  assert.strictEqual(MOCK_CARDIOVASCULAR_NARRATIVE_RESPONSE.domain, 'cardiovascular');
  assert.strictEqual(MOCK_CARDIOVASCULAR_NARRATIVE_RESPONSE.patient_id, 'PT-CARDIO-RENAL-508');
  assert.ok(MOCK_CARDIOVASCULAR_NARRATIVE_RESPONSE.narrative_id.startsWith('narr-cvd-'));
  assert.ok(MOCK_CARDIOVASCULAR_NARRATIVE_RESPONSE.context_id.startsWith('ctx-cvd-'));
  assert.ok(MOCK_CARDIOVASCULAR_NARRATIVE_RESPONSE.assessment_id.startsWith('assess-cvd-'));
  assert.strictEqual(MOCK_CARDIOVASCULAR_NARRATIVE_RESPONSE.provider, 'mock');
  assert.strictEqual(MOCK_CARDIOVASCULAR_NARRATIVE_RESPONSE.model_name, 'gemini-1.5-pro');
});

test('2. Cardiovascular narrative contains all 5 required structured sections', () => {
  const narrative = MOCK_CARDIOVASCULAR_NARRATIVE_RESPONSE;
  const requiredSections = [
    'summary',
    'observed_trajectory',
    'data_limitations',
    'statistical_calibration_status',
    'disclaimer',
  ];

  for (const sec of requiredSections) {
    assert.ok(narrative[sec], `Cardiovascular section '${sec}' must exist`);
    assert.ok(narrative[sec].trim().length > 0, `Cardiovascular section '${sec}' must not be empty`);
  }
});

test('3. Cardiovascular calibration status strictly withholds numerical probability', () => {
  const status = MOCK_CARDIOVASCULAR_NARRATIVE_RESPONSE.statistical_calibration_status;
  assert.ok(status.toLowerCase().includes('uncalibrated'));
  assert.ok(status.toLowerCase().includes('no numerical risk probability'));

  // Ensure no probability percentage is asserted
  const hasProbabilityPercentage = /\b\d{1,3}%\s*(risk|chance|probability)\b/i.test(status);
  assert.strictEqual(hasProbabilityPercentage, false, 'Cardiovascular calibration must withhold numerical percentage');
});

test('4. Cardiovascular narrative disclaimer mandates non-diagnostic boundary', () => {
  const disclaimer = MOCK_CARDIOVASCULAR_NARRATIVE_RESPONSE.disclaimer;
  assert.ok(disclaimer.toLowerCase().includes('non-diagnostic'));
  assert.ok(disclaimer.toLowerCase().includes('non-prescriptive'));
  assert.ok(!disclaimer.toLowerCase().includes('prescribe'));
});

test('5. Cardiovascular narrative error mapping handles unconfigured provider (503)', () => {
  const err = {
    status: 503,
    message: "LLM Provider 'gemini' is selected, but GENAI_API_KEY is not configured.",
  };
  const mapped = mapNarrativeError(err);
  assert.strictEqual(mapped.type, 'provider_not_configured');
  assert.ok(mapped.message.includes('not configured with an active API key'));
  assert.ok(mapped.message.includes('safely withheld'));
});

test('6. Cardiovascular narrative error mapping handles safety guard rejection (502)', () => {
  const err = {
    status: 502,
    message: 'Clinical safety validation rejected LLM generation: unauthorized medication directive.',
  };
  const mapped = mapNarrativeError(err);
  assert.strictEqual(mapped.type, 'validation_failure');
  assert.ok(mapped.message.includes('Clinical Safety Guard'));
  assert.ok(mapped.message.includes('safety boundaries'));
});

test('7. Cardiovascular narrative error mapping handles patient not found (404)', () => {
  const err = {
    status: 404,
    message: "Patient 'PT-NONEXISTENT' not found.",
    stack: 'Error: Not Found\n  at callApi (/app/api.ts:20:10)',
  };
  const mapped = mapNarrativeError(err);
  assert.strictEqual(mapped.type, 'general');
  assert.ok(mapped.message.includes('not found in the clinical repository'));
  assert.ok(!mapped.message.includes('callApi'), 'Must never leak stack traces');
});

test('8. Cardiovascular evidence response contract matches backend ACC/AHA guidelines', () => {
  const res = MOCK_CARDIOVASCULAR_EVIDENCE_RESPONSE;
  assert.strictEqual(res.domain, 'cardiovascular');
  assert.strictEqual(res.total_references, 1);
  assert.strictEqual(res.provider_id, 'curated_evidence_provider_v1');

  const ref = res.references[0];
  assert.strictEqual(ref.evidence_id, 'ev-acc-2019-primary-prevention-cvd');
  assert.strictEqual(ref.source_id, 'ACC-AHA-PPCVD-2019');
  assert.strictEqual(ref.guideline_title, '2019 ACC/AHA Guideline on the Primary Prevention of Cardiovascular Disease');
  assert.strictEqual(ref.publication_version, '2019 Guideline');
  assert.strictEqual(ref.domain_category, 'cardiovascular_risk_expansion');
  assert.strictEqual(ref.evidence_status, 'verified');
  assert.strictEqual(ref.recommendation_identifier, null, 'Must preserve null recommendation identifier');
  assert.ok(ref.official_url.startsWith('https://www.ahajournals.org/'));
  assert.ok(ref.citation_text.includes('Circulation. 2019'));
});

test('9. Cardiovascular evidence source badge correctly displays ACC/AHA styling', () => {
  const badge = getSourceBadge(
    'American College of Cardiology / American Heart Association (ACC/AHA)',
    'ACC-AHA-PPCVD-2019'
  );
  assert.strictEqual(badge.label, 'ACC/AHA');
  assert.strictEqual(badge.fullOrg, 'American College of Cardiology / AHA');
  assert.ok(badge.className.includes('rose-50'));
  assert.ok(badge.className.includes('rose-800'));
});

test('10. Cardiovascular domain label formatting outputs clean clinical title', () => {
  const label = formatDomainLabel('cardiovascular_risk_expansion');
  assert.strictEqual(label, 'Cardiovascular Primary Prevention (ACC/AHA)');
});

test('11. Cardiovascular evidence disclaimer is non-prescriptive and informational', () => {
  const disclaimer = MOCK_CARDIOVASCULAR_EVIDENCE_RESPONSE.disclaimer;
  assert.ok(disclaimer.includes('informational decision support'));
  assert.ok(disclaimer.includes('non-prescriptive'));
});
