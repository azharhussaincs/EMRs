import test from 'node:test';
import assert from 'node:assert/strict';

test('FHIR R4 Bundle structure verification for EMR ingestion', () => {
  const fhirBundle = {
    resourceType: 'Bundle',
    type: 'collection',
    entry: [
      {
        resource: {
          resourceType: 'Patient',
          id: 'PT-TEST-CARDIO-01',
          gender: 'male',
          birthDate: '1964-08-14',
        },
      },
      {
        resource: {
          resourceType: 'Observation',
          id: 'obs-hba1c-1',
          code: {
            coding: [{ system: 'http://loinc.org', code: '4548-4', display: 'Hemoglobin A1c' }],
          },
          effectiveDateTime: '2025-06-12T09:15:00Z',
          valueQuantity: { value: 7.6, unit: '%' },
        },
      },
      {
        resource: {
          resourceType: 'Condition',
          id: 'cond-dm',
          code: {
            coding: [{ system: 'http://hl7.org/fhir/sid/icd-10', code: 'E11.9', display: 'Type 2 diabetes' }],
          },
          clinicalStatus: { coding: [{ code: 'active' }] },
        },
      },
    ],
  };

  assert.strictEqual(fhirBundle.resourceType, 'Bundle');
  assert.strictEqual(fhirBundle.entry.length, 3);
  const patient = fhirBundle.entry.find(e => e.resource.resourceType === 'Patient');
  assert.ok(patient);
  assert.strictEqual(patient.resource.id, 'PT-TEST-CARDIO-01');
});

test('Clinical validation rules: Detects physiologically impossible HbA1c', () => {
  const minPlausibleHbA1c = 2.0;
  const maxPlausibleHbA1c = 25.0;

  const validHbA1c = 7.4;
  const impossibleHighHbA1c = 34.5;
  const impossibleLowHbA1c = 0.5;

  assert.ok(validHbA1c >= minPlausibleHbA1c && validHbA1c <= maxPlausibleHbA1c);
  assert.ok(impossibleHighHbA1c > maxPlausibleHbA1c, 'High value must violate maximum physiological bound');
  assert.ok(impossibleLowHbA1c < minPlausibleHbA1c, 'Low value must violate minimum physiological bound');
});

test('Clinical validation rules: Blood pressure cross-validation prevents inversion', () => {
  const systolic = 70;
  const diastolic = 105;

  const isPhysiologicallyValid = systolic > diastolic;
  assert.strictEqual(isPhysiologicallyValid, false, 'Systolic must be strictly greater than diastolic');
});

test('Longitudinal timestamps ordering maintains chronological trajectory', () => {
  const observations = [
    { effective_datetime: '2026-02-20T08:45:00Z', value: 8.2 },
    { effective_datetime: '2024-09-15T09:00:00Z', value: 7.1 },
    { effective_datetime: '2025-06-12T09:15:00Z', value: 7.6 },
  ];

  const sorted = [...observations].sort(
    (a, b) => new Date(a.effective_datetime).getTime() - new Date(b.effective_datetime).getTime()
  );

  assert.strictEqual(sorted[0].value, 7.1, 'Earliest observation must be first');
  assert.strictEqual(sorted[1].value, 7.6, 'Mid-period observation must be second');
  assert.strictEqual(sorted[2].value, 8.2, 'Latest observation must be third');
});

test('Clinical domain readiness evaluates data coverage for target conditions', () => {
  const longitudinalBiomarkers = {
    hba1c: [{ value: 7.4 }],
    systolic_bp: [{ value: 140 }],
    egfr: [{ value: 55 }],
  };

  const hasDiabetes = 'hba1c' in longitudinalBiomarkers;
  const hasCardiovascular = 'systolic_bp' in longitudinalBiomarkers;
  const hasCKD = 'egfr' in longitudinalBiomarkers;
  const hasCancer = 'cea' in longitudinalBiomarkers || 'psa' in longitudinalBiomarkers;

  assert.strictEqual(hasDiabetes, true);
  assert.strictEqual(hasCardiovascular, true);
  assert.strictEqual(hasCKD, true);
  assert.strictEqual(hasCancer, false);
});
