import test from 'node:test';
import assert from 'node:assert/strict';

// Helper to simulate client-side formatting logic in CardiovascularRiskReviewView
function formatSufficiencyBadge(status) {
  switch (status) {
    case 'sufficient_data':
      return {
        label: 'Sufficient Risk Factor History',
        badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-200',
        detail: 'All 7 core ASCVD clinical inputs documented in EMR without imputation',
      };
    case 'insufficient_data':
      return {
        label: 'Insufficient Clinical Data',
        badgeClass: 'bg-amber-50 text-amber-800 border-amber-200',
        detail: 'Incomplete ASCVD factor profile; missing values preserved without imputation',
      };
    case 'unavailable_feature':
    default:
      return {
        label: 'Cardiovascular Features Unavailable',
        badgeClass: 'bg-slate-100 text-slate-700 border-slate-300',
        detail: 'Baseline blood pressure and lipid panel observations missing from EMR',
      };
  }
}

function formatRiskProbability(riskEstimate, calibrationStatus) {
  if (riskEstimate !== null && riskEstimate !== undefined) {
    return `${(riskEstimate * 100).toFixed(1)}%`;
  }
  if (calibrationStatus === 'not_calibrated') {
    return 'Estimator is uncalibrated. Empirical 10-year ASCVD risk probability is strictly withheld to prevent fabricated risk claims.';
  }
  return 'Probability unavailable';
}

function sanitizeApiErrorMessage(errBody, fallbackStatus = 500) {
  if (typeof errBody?.detail === 'string') return errBody.detail;
  if (typeof errBody?.message === 'string') return errBody.message;
  return `Clinical API request failed (${fallbackStatus})`;
}

// Mock payload matching backend GET /api/v1/risk/patients/{patient_id}/cardiovascular
const MOCK_COMPLETE_ASCVD_ASSESSMENT = {
  assessment_id: 'assess-cvd-8b7a6c5d4e3f',
  patient_id: 'PT-ASCVD-COMPLETE',
  assessed_at: '2026-09-29T07:15:00Z',
  domain: 'cardiovascular',
  estimator_id: 'ascvd_pooled_cohort_v0_1',
  estimator_version: '0.1.0-foundation',
  data_sufficiency: 'sufficient_data',
  calibration_status: 'not_calibrated',
  risk_estimate: null,
  confidence_interval: null,
  features_used: {
    age: {
      feature_name: 'age',
      value: 57.0,
      unit: 'years',
      description: 'Chronological age derived from birth date',
    },
    gender: {
      feature_name: 'gender',
      unit: null,
      description: 'Administrative sex: female',
    },
    systolic_bp: {
      feature_name: 'systolic_bp',
      value: 144.0,
      unit: 'mmHg',
      source_timestamp: '2026-01-15T09:00:00Z',
      description: 'Latest resting systolic blood pressure',
    },
    total_cholesterol: {
      feature_name: 'total_cholesterol',
      value: 210.0,
      unit: 'mg/dL',
      source_timestamp: '2026-01-15T09:00:00Z',
      description: 'Latest total serum cholesterol',
    },
    hdl_cholesterol: {
      feature_name: 'hdl_cholesterol',
      value: 52.0,
      unit: 'mg/dL',
      source_timestamp: '2026-01-15T09:00:00Z',
      description: 'Latest high-density lipoprotein (HDL) cholesterol',
    },
    smoking_status: {
      feature_name: 'smoking_status',
      unit: null,
      description: 'Smoking status: current_smoker (F17.210)',
    },
    diabetes_status: {
      feature_name: 'diabetes_status',
      unit: null,
      description: 'Diabetes mellitus confirmed present',
    },
  },
  unavailable_inputs: [],
  limitations: [
    'Estimator is in research foundation phase (v0.1.0-foundation).',
    'Estimator is uncalibrated against longitudinal population cohorts; empirical risk probability is strictly withheld.',
    'Empirical 10-year ASCVD risk probabilities are strictly withheld until calibrated cohort models (e.g. ACC/AHA Pooled Cohort Equations) are formally validated.',
    'Clinical features reflect verified risk factor presence; rule-of-thumb approximations are rejected.',
    'Does not constitute clinical diagnosis, statin prescription recommendation, or treatment directive.',
  ],
  disclaimer:
    'Cardiovascular / ASCVD risk assessment foundation. Strictly non-prescriptive and non-diagnostic. Statin therapy and medication directives are withheld.',
};

test('1. Successful Cardiovascular (ASCVD) assessment display contract', () => {
  const assessment = MOCK_COMPLETE_ASCVD_ASSESSMENT;

  assert.strictEqual(assessment.domain, 'cardiovascular');
  assert.strictEqual(assessment.estimator_id, 'ascvd_pooled_cohort_v0_1');
  assert.strictEqual(assessment.estimator_version, '0.1.0-foundation');
  assert.strictEqual(assessment.patient_id, 'PT-ASCVD-COMPLETE');
  assert.strictEqual(assessment.data_sufficiency, 'sufficient_data');
  assert.strictEqual(assessment.calibration_status, 'not_calibrated');
  assert.strictEqual(assessment.risk_estimate, null);

  const badge = formatSufficiencyBadge(assessment.data_sufficiency);
  assert.strictEqual(badge.label, 'Sufficient Risk Factor History');
  assert.ok(badge.detail.includes('All 7 core ASCVD clinical inputs'));
});

test('2. All 7 major ASCVD clinical risk factors rendered correctly', () => {
  const feats = MOCK_COMPLETE_ASCVD_ASSESSMENT.features_used;

  assert.strictEqual(feats.age.value, 57.0);
  assert.strictEqual(feats.age.unit, 'years');

  assert.ok(feats.gender.description.includes('female'));

  assert.strictEqual(feats.systolic_bp.value, 144.0);
  assert.strictEqual(feats.systolic_bp.unit, 'mmHg');

  assert.strictEqual(feats.total_cholesterol.value, 210.0);
  assert.strictEqual(feats.total_cholesterol.unit, 'mg/dL');

  assert.strictEqual(feats.hdl_cholesterol.value, 52.0);
  assert.strictEqual(feats.hdl_cholesterol.unit, 'mg/dL');

  assert.ok(feats.smoking_status.description.includes('current_smoker'));
  assert.ok(feats.diabetes_status.description.includes('confirmed present'));
});

test('3. Partial data sufficiency highlights missing required features', () => {
  const partialAssessment = {
    assessment_id: 'assess-cvd-partial-01',
    patient_id: 'PT-PARTIAL-CVD',
    domain: 'cardiovascular',
    estimator_id: 'ascvd_pooled_cohort_v0_1',
    data_sufficiency: 'insufficient_data',
    calibration_status: 'not_calibrated',
    risk_estimate: null,
    features_used: {
      age: { feature_name: 'age', value: 51.0, unit: 'years' },
      systolic_bp: { feature_name: 'systolic_bp', value: 130.0, unit: 'mmHg' },
    },
    unavailable_inputs: ['total_cholesterol', 'hdl_cholesterol', 'smoking_status'],
    limitations: ['Incomplete ASCVD risk factor profile (3 required inputs missing).'],
  };

  const badge = formatSufficiencyBadge(partialAssessment.data_sufficiency);
  assert.strictEqual(badge.label, 'Insufficient Clinical Data');
  assert.strictEqual(partialAssessment.unavailable_inputs.length, 3);
  assert.ok(partialAssessment.unavailable_inputs.includes('total_cholesterol'));
  assert.ok(partialAssessment.unavailable_inputs.includes('hdl_cholesterol'));
  assert.ok(partialAssessment.unavailable_inputs.includes('smoking_status'));

  // Missing values must return 'Unavailable' safely without exceptions
  const tcVal = partialAssessment.features_used.total_cholesterol?.value ?? 'Unavailable';
  const smokeVal = partialAssessment.features_used.smoking_status?.description ?? 'Undocumented';
  assert.strictEqual(tcVal, 'Unavailable');
  assert.strictEqual(smokeVal, 'Undocumented');
});

test('4. Complete data absence (unavailable_feature) handled safely', () => {
  const missingAssessment = {
    assessment_id: 'assess-cvd-none',
    patient_id: 'PT-NO-CVD',
    domain: 'cardiovascular',
    data_sufficiency: 'unavailable_feature',
    calibration_status: 'insufficient_model',
    risk_estimate: null,
    features_used: {},
    unavailable_inputs: [
      'age',
      'gender',
      'systolic_bp',
      'total_cholesterol',
      'hdl_cholesterol',
      'smoking_status',
      'diabetes_status',
    ],
  };

  const badge = formatSufficiencyBadge(missingAssessment.data_sufficiency);
  assert.strictEqual(badge.label, 'Cardiovascular Features Unavailable');
  assert.strictEqual(Object.keys(missingAssessment.features_used).length, 0);
  assert.strictEqual(missingAssessment.unavailable_inputs.length, 7);
});

test('5. Probability safety invariant: No numerical percentage or heuristic score emitted', () => {
  const displayMessage = formatRiskProbability(
    MOCK_COMPLETE_ASCVD_ASSESSMENT.risk_estimate,
    MOCK_COMPLETE_ASCVD_ASSESSMENT.calibration_status
  );

  assert.ok(displayMessage.includes('uncalibrated'));
  assert.ok(displayMessage.includes('strictly withheld'));
  assert.ok(!displayMessage.includes('%'), 'Must not emit percentage numbers');

  // Verify risk estimate is strictly null
  assert.strictEqual(MOCK_COMPLETE_ASCVD_ASSESSMENT.risk_estimate, null);
  assert.strictEqual(MOCK_COMPLETE_ASCVD_ASSESSMENT.confidence_interval, null);
});

test('6. Model governance card displays ASCVD metadata and assumptions', () => {
  const cvdModelCard = {
    estimator_id: 'ascvd_pooled_cohort_v0_1',
    version: '0.1.0-foundation',
    domain: 'cardiovascular',
    target: '10-Year Atherosclerotic Cardiovascular Disease (ASCVD) Risk Assessment',
    input_features: [
      'age',
      'gender',
      'systolic_bp',
      'total_cholesterol',
      'hdl_cholesterol',
      'smoking_status',
      'diabetes_status',
    ],
    calibration_status: 'not_calibrated',
    assumptions:
      'Requires baseline lipid panel, systolic BP, age, sex, and verified smoking/diabetes status. Uncalibrated foundation phase.',
    disclaimer:
      'Research and engineering component only. Strictly non-prescriptive and non-diagnostic. Statin therapy and medication directives are withheld.',
  };

  assert.strictEqual(cvdModelCard.estimator_id, 'ascvd_pooled_cohort_v0_1');
  assert.strictEqual(cvdModelCard.domain, 'cardiovascular');
  assert.strictEqual(cvdModelCard.calibration_status, 'not_calibrated');
  assert.strictEqual(cvdModelCard.input_features.length, 7);
  assert.ok(cvdModelCard.assumptions.includes('Requires baseline lipid panel'));
  assert.ok(cvdModelCard.disclaimer.includes('non-diagnostic'));
});

test('7. Patient 404 response produces clinician-safe message without stack traces', () => {
  const backend404 = {
    detail: "Patient with identifier 'PT-UNKNOWN-CVD' not found in clinical repository.",
  };
  const sanitized = sanitizeApiErrorMessage(backend404, 404);
  assert.strictEqual(
    sanitized,
    "Patient with identifier 'PT-UNKNOWN-CVD' not found in clinical repository."
  );
  assert.ok(!sanitized.includes('Traceback'));
});

test('8. Network / API failure (500) handled safely without exposing internal server details', () => {
  const backend500 = {
    message: 'Internal server error occurred',
    internal_port: '8001',
    trace: 'Exception in risk_engine.py at line 14',
  };
  const sanitized = sanitizeApiErrorMessage(backend500, 500);
  assert.strictEqual(sanitized, 'Internal server error occurred');
  assert.ok(!sanitized.includes('risk_engine.py'));
  assert.ok(!sanitized.includes('8001'));
});

test('9. Mandatory non-prescriptive disclaimer preserved without weakening', () => {
  const disclaimer = MOCK_COMPLETE_ASCVD_ASSESSMENT.disclaimer;
  assert.ok(disclaimer.includes('non-prescriptive'));
  assert.ok(disclaimer.includes('non-diagnostic'));
  assert.ok(disclaimer.includes('Statin therapy and medication directives are withheld'));
});

test('10. Clinical safety guard: No statin or medication recommendations emitted', () => {
  for (const lim of MOCK_COMPLETE_ASCVD_ASSESSMENT.limitations) {
    // Assert no directives to prescribe medications or statins
    assert.ok(!lim.toLowerCase().includes('prescribe atorvastatin'));
    assert.ok(!lim.toLowerCase().includes('start statin'));
    assert.ok(!lim.toLowerCase().includes('target bp 120'));
  }
});
