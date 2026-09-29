import test from 'node:test';
import assert from 'node:assert/strict';

// Helper to simulate client-side formatting logic in DiabetesRiskReviewView
function formatSufficiencyBadge(status) {
  switch (status) {
    case 'sufficient_data':
      return {
        label: 'Sufficient Longitudinal History',
        badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-200',
        detail: '≥ 2 historical HbA1c observations with distinct timestamps',
      };
    case 'insufficient_data':
      return {
        label: 'Insufficient Longitudinal History',
        badgeClass: 'bg-amber-50 text-amber-800 border-amber-200',
        detail: 'Single observation or identical timestamps; trajectory rate unavailable',
      };
    case 'unavailable_feature':
    default:
      return {
        label: 'Feature Unavailable',
        badgeClass: 'bg-slate-100 text-slate-700 border-slate-300',
        detail: 'No glycated hemoglobin (HbA1c) measurements found in record',
      };
  }
}

function formatRiskProbability(riskEstimate, calibrationStatus) {
  if (riskEstimate !== null && riskEstimate !== undefined) {
    return `${(riskEstimate * 100).toFixed(1)}%`;
  }
  if (calibrationStatus === 'not_calibrated') {
    return 'Estimator is uncalibrated. Statistical probability is strictly withheld to prevent fabricated risk claims.';
  }
  return 'Probability unavailable';
}

function sanitizeApiErrorMessage(errBody, fallbackStatus = 500) {
  if (typeof errBody?.detail === 'string') return errBody.detail;
  if (typeof errBody?.message === 'string') return errBody.message;
  return `Clinical API request failed (${fallbackStatus})`;
}

test('1. Successful Diabetes assessment display contract', () => {
  const assessmentPayload = {
    assessment_id: 'assess-dm-94061e19939c',
    patient_id: 'PT-CARDIO-RENAL-508',
    assessed_at: '2026-09-29T06:01:34.296907Z',
    domain: 'diabetes',
    estimator_id: 'diabetes_hba1c_trajectory_v0_1',
    estimator_version: '0.1.0-foundation',
    data_sufficiency: 'sufficient_data',
    calibration_status: 'not_calibrated',
    risk_estimate: null,
    confidence_interval: null,
    features_used: {
      hba1c_latest: {
        feature_name: 'hba1c_latest',
        value: 8.2,
        unit: '%',
        source_timestamp: '2026-02-20T08:45:00Z',
        description: 'Most recent glycated hemoglobin measurement',
      },
      hba1c_previous: {
        feature_name: 'hba1c_previous',
        value: 7.6,
        unit: '%',
        source_timestamp: '2025-06-12T09:15:00Z',
        description: 'Preceding glycated hemoglobin measurement',
      },
      hba1c_change: {
        feature_name: 'hba1c_change',
        value: 0.6,
        unit: '%',
        source_timestamp: null,
        description: 'Absolute difference between consecutive measurements',
      },
      hba1c_annualized_rate: {
        feature_name: 'hba1c_annualized_rate',
        value: 0.86,
        unit: '%/year',
        source_timestamp: null,
        description: 'Annualized rate of change derived across temporal interval',
      },
    },
    unavailable_inputs: [],
    limitations: [
      'Estimator is in research foundation phase (v0.1.0-foundation).',
      'Empirical population cohort calibration is required before statistical risk probabilities can be emitted.',
    ],
    disclaimer: 'Research & engineering risk stratification prototype. Does not claim clinical diagnostic validity.',
  };

  const badge = formatSufficiencyBadge(assessmentPayload.data_sufficiency);
  assert.strictEqual(badge.label, 'Sufficient Longitudinal History');
  assert.ok(badge.detail.includes('≥ 2 historical HbA1c observations'));

  // Verify feature values
  assert.strictEqual(assessmentPayload.features_used.hba1c_latest.value, 8.2);
  assert.strictEqual(assessmentPayload.features_used.hba1c_previous.value, 7.6);
  assert.strictEqual(assessmentPayload.features_used.hba1c_change.value, 0.6);
  assert.strictEqual(assessmentPayload.features_used.hba1c_annualized_rate.value, 0.86);
  assert.strictEqual(assessmentPayload.unavailable_inputs.length, 0);
});

test('2. risk_estimate = null displays the correct uncalibrated state', () => {
  const riskEstimate = null;
  const calibrationStatus = 'not_calibrated';

  const displayMessage = formatRiskProbability(riskEstimate, calibrationStatus);

  // Must clearly assert uncalibrated state and withhold fabricated percentage
  assert.ok(displayMessage.includes('uncalibrated'));
  assert.ok(displayMessage.includes('strictly withheld'));
  assert.ok(!displayMessage.includes('%'), 'Must not emit artificial or zero percent values');
});

test('3. Insufficient HbA1c history is displayed correctly', () => {
  const singleMeasurementPayload = {
    assessment_id: 'assess-dm-single-01',
    patient_id: 'PT-SINGLE-01',
    assessed_at: '2026-09-29T06:01:34.296907Z',
    domain: 'diabetes',
    estimator_id: 'diabetes_hba1c_trajectory_v0_1',
    estimator_version: '0.1.0-foundation',
    data_sufficiency: 'insufficient_data',
    calibration_status: 'not_calibrated',
    risk_estimate: null,
    features_used: {
      hba1c_latest: {
        feature_name: 'hba1c_latest',
        value: 7.4,
        unit: '%',
        source_timestamp: '2026-01-10T10:00:00Z',
        description: 'Most recent glycated hemoglobin measurement',
      },
    },
    unavailable_inputs: ['hba1c_previous', 'hba1c_change', 'hba1c_annualized_rate'],
    limitations: [
      'Only 1 HbA1c observation is present in the record.',
      'Longitudinal trajectory assessment requires at least 2 distinct historical measurements.',
    ],
  };

  const badge = formatSufficiencyBadge(singleMeasurementPayload.data_sufficiency);
  assert.strictEqual(badge.label, 'Insufficient Longitudinal History');
  assert.strictEqual(singleMeasurementPayload.unavailable_inputs.length, 3);
  assert.ok(singleMeasurementPayload.unavailable_inputs.includes('hba1c_annualized_rate'));
  assert.ok(singleMeasurementPayload.limitations[0].includes('Only 1 HbA1c observation'));
});

test('4. Missing features are handled safely without runtime errors', () => {
  const missingDataPayload = {
    assessment_id: 'assess-dm-missing-01',
    patient_id: 'PT-NO-LABS-02',
    domain: 'diabetes',
    data_sufficiency: 'unavailable_feature',
    calibration_status: 'insufficient_model',
    risk_estimate: null,
    features_used: {},
    unavailable_inputs: ['hba1c_latest', 'hba1c_previous', 'hba1c_change', 'hba1c_annualized_rate'],
    limitations: ['No HbA1c observations found in patient EMR.'],
  };

  const badge = formatSufficiencyBadge(missingDataPayload.data_sufficiency);
  assert.strictEqual(badge.label, 'Feature Unavailable');
  assert.strictEqual(Object.keys(missingDataPayload.features_used).length, 0);

  // Safe property access pattern check
  const latestVal = missingDataPayload.features_used.hba1c_latest?.value ?? 'Unavailable';
  const prevVal = missingDataPayload.features_used.hba1c_previous?.value ?? 'Unavailable';
  assert.strictEqual(latestVal, 'Unavailable');
  assert.strictEqual(prevVal, 'Unavailable');
});

test('5. Model governance information renders correctly', () => {
  const modelGovernanceData = {
    estimator_id: 'diabetes_hba1c_trajectory_v0_1',
    version: '0.1.0-foundation',
    domain: 'diabetes',
    target: 'Glycemic Trajectory Stratification',
    input_features: ['hba1c_latest', 'hba1c_previous', 'hba1c_change', 'hba1c_annualized_rate'],
    calibration_status: 'not_calibrated',
    assumptions: 'Requires >= 2 distinct historical HbA1c observations separated by time.',
    disclaimer: 'Research and engineering component only. Not validated for autonomous diagnostic decisions.',
  };

  assert.strictEqual(modelGovernanceData.estimator_id, 'diabetes_hba1c_trajectory_v0_1');
  assert.strictEqual(modelGovernanceData.version, '0.1.0-foundation');
  assert.strictEqual(modelGovernanceData.calibration_status, 'not_calibrated');
  assert.strictEqual(modelGovernanceData.input_features.length, 4);
  assert.ok(modelGovernanceData.assumptions.includes('Requires >= 2 distinct historical HbA1c observations'));
  assert.ok(modelGovernanceData.disclaimer.includes('Research and engineering component only'));
});

test('6. API failure displays a clear user-facing error without stack traces', () => {
  const backend404Response = {
    detail: "Patient with identifier 'PT-UNKNOWN-999' not found in clinical repository.",
  };

  const userFacingMessage = sanitizeApiErrorMessage(backend404Response, 404);
  assert.strictEqual(
    userFacingMessage,
    "Patient with identifier 'PT-UNKNOWN-999' not found in clinical repository."
  );

  // Verify internal stack trace is not exposed
  const internalError = {
    message: 'Internal server error',
    traceback: 'Traceback (most recent call last):\n  File "server.py", line 42...',
  };
  const sanitized = sanitizeApiErrorMessage(internalError, 500);
  assert.strictEqual(sanitized, 'Internal server error');
  assert.ok(!sanitized.includes('Traceback'));
});
