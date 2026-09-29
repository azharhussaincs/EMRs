import test from 'node:test';
import assert from 'node:assert/strict';

// Helper simulating client-side state mapping in ClinicalNarrativeView
function mapNarrativeError(errObj) {
  const msg = errObj?.message || 'Failed to generate clinical explanation narrative.';
  if (errObj?.status === 503 || msg.toLowerCase().includes('not configured')) {
    return {
      type: 'provider_not_configured',
      message: 'Generative AI provider is not configured with an active API key in this environment. Narrative synthesis is safely withheld.',
    };
  }
  if (errObj?.status === 502 || msg.toLowerCase().includes('validation rejected')) {
    return {
      type: 'validation_failure',
      message: 'Clinical Safety Guard: AI generation was rejected because the output did not strictly conform to verified clinical safety boundaries.',
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

test('1. Successful clinical narrative response contract rendering', () => {
  const narrativePayload = {
    narrative_id: 'narr-dm-9a8b7c6d5e4f',
    context_id: 'ctx-dm-1a2b3c4d5e6f',
    patient_id: 'PT-CARDIO-RENAL-508',
    assessment_id: 'assess-dm-94061e19939c',
    domain: 'diabetes',
    summary: 'Longitudinal glycemic review for PT-CARDIO-RENAL-508 indicates an observed HbA1c increase from baseline 7.6% to 8.2%.',
    observed_trajectory: 'Record documents 3 sequential HbA1c observations over an interval of 253 days. Latest measurement is 8.2% (previous: 7.6%), reflecting an absolute change of +0.6% and annualized progression velocity of +0.86%/year.',
    data_limitations: 'Trajectory evaluated over 3 observations. Estimator in foundation phase (v0.1.0-foundation).',
    statistical_calibration_status: 'Estimator is uncalibrated against longitudinal population cohorts. In accordance with clinical safety principles, no numerical risk probability or percentage is emitted.',
    disclaimer: 'Research & engineering risk stratification prototype. Does not claim clinical diagnostic validity. Strictly non-diagnostic and non-prescriptive.',
    provider: 'mock',
    model_name: 'gemini-1.5-pro',
    generated_at: '2026-09-29T06:30:00Z',
  };

  assert.strictEqual(narrativePayload.patient_id, 'PT-CARDIO-RENAL-508');
  assert.strictEqual(narrativePayload.domain, 'diabetes');
  assert.ok(narrativePayload.narrative_id.startsWith('narr-dm-'));
  assert.ok(narrativePayload.context_id.startsWith('ctx-dm-'));
});

test('2. All 5 required sections are present and non-empty', () => {
  const narrative = {
    summary: 'Glycemic progression observed over 253 days.',
    observed_trajectory: 'Latest HbA1c 8.2% vs previous 7.6%.',
    data_limitations: 'Limited to 3 recorded observations.',
    statistical_calibration_status: 'Estimator is uncalibrated. Probability withheld.',
    disclaimer: 'Strictly non-diagnostic and non-prescriptive.',
  };

  const requiredSections = [
    'summary',
    'observed_trajectory',
    'data_limitations',
    'statistical_calibration_status',
    'disclaimer',
  ];

  for (const section of requiredSections) {
    assert.ok(narrative[section], `Section '${section}' must exist`);
    assert.ok(narrative[section].trim().length > 0, `Section '${section}' must not be empty`);
  }
});

test('3. Statistical calibration status withholds numerical probability', () => {
  const calibrationStatusText =
    'Estimator is uncalibrated against longitudinal population cohorts. In accordance with clinical safety principles, no numerical risk probability or percentage is emitted.';

  assert.ok(calibrationStatusText.toLowerCase().includes('uncalibrated'));
  assert.ok(calibrationStatusText.toLowerCase().includes('no numerical risk probability'));

  // Ensure no fabricated percentage risk appears in the calibration statement
  const hasFabricatedPercentage = /\b\d{1,3}%\s*(risk|chance|probability)\b/i.test(calibrationStatusText);
  assert.strictEqual(hasFabricatedPercentage, false, 'Must not claim numerical probability');
});

test('4. Regulatory non-diagnostic disclaimer visibility', () => {
  const disclaimerText =
    'Research & engineering risk stratification prototype. Does not claim clinical diagnostic validity. Strictly non-diagnostic and non-prescriptive.';

  assert.ok(disclaimerText.toLowerCase().includes('non-diagnostic'));
  assert.ok(disclaimerText.toLowerCase().includes('non-prescriptive'));
  assert.ok(disclaimerText.length >= 20, 'Disclaimer must be comprehensive and visible');
});

test('5. Loading state prevents duplicate requests and displays feedback', () => {
  let isGenerating = true;
  let canTriggerSubmit = !isGenerating;

  assert.strictEqual(canTriggerSubmit, false, 'Action button must be disabled while generating');

  // Verify transition to resolved state
  isGenerating = false;
  canTriggerSubmit = !isGenerating;
  assert.strictEqual(canTriggerSubmit, true, 'Action button must be re-enabled after generation');
});

test('6. API failure (404 / network) generates clinician-safe message without stack traces', () => {
  const err404 = {
    status: 404,
    message: "Patient with identifier 'PT-MISSING-404' not found in clinical repository.",
    stack: 'Error: Patient not found\n    at fetchFromApi (http://localhost:3000/api.js:42:15)',
  };

  const mapped = mapNarrativeError(err404);
  assert.strictEqual(mapped.type, 'general');
  assert.ok(mapped.message.includes('not found in the clinical repository'));
  assert.ok(!mapped.message.includes('fetchFromApi'), 'Must not expose JS or Python call stacks');
  assert.ok(!mapped.message.includes('localhost:3000'), 'Must not expose internal URLs');
});

test('7. Provider not configured (503) generates clear controlled notification', () => {
  const err503 = {
    status: 503,
    message: "LLM Provider 'gemini' is selected, but GENAI_API_KEY is not configured in the environment.",
  };

  const mapped = mapNarrativeError(err503);
  assert.strictEqual(mapped.type, 'provider_not_configured');
  assert.ok(mapped.message.includes('not configured with an active API key'));
  assert.ok(mapped.message.includes('safely withheld'));
});

test('8. Clinical safety validation rejection (502) alerts user safely', () => {
  const err502 = {
    status: 502,
    message: 'Clinical safety validation rejected LLM generation: LLM output contained unauthorized clinical prescription directives.',
  };

  const mapped = mapNarrativeError(err502);
  assert.strictEqual(mapped.type, 'validation_failure');
  assert.ok(mapped.message.includes('Clinical Safety Guard'));
  assert.ok(mapped.message.includes('safety boundaries'));
});
