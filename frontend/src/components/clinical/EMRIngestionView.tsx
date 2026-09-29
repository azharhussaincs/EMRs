'use client';

import React, { useState } from 'react';
import {
  FileUp,
  CheckCircle2,
  AlertCircle,
  FileText,
  Activity,
  Calendar,
  Pill,
  Stethoscope,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import {
  validateEMRPayload,
  ingestEMRPayload,
  fetchSampleFHIR,
} from '@/lib/api';
import { DiabetesRiskReviewView } from './DiabetesRiskReviewView';
import { CardiovascularRiskReviewView } from './CardiovascularRiskReviewView';
import type {
  NormalizedPatientRecord,
  ClinicalValidationErrorItem,
  EMRIngestionSuccessResponse,
} from '@/types/clinical';

export const EMRIngestionView: React.FC = () => {
  const [jsonText, setJsonText] = useState<string>('');
  const [fileName, setFileName] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [validationErrors, setValidationErrors] = useState<ClinicalValidationErrorItem[]>([]);
  const [successResponse, setSuccessResponse] = useState<EMRIngestionSuccessResponse | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState<boolean>(false);
  const [selectedRiskDomain, setSelectedRiskDomain] = useState<'diabetes' | 'cardiovascular'>('diabetes');

  // Load genuine sample FHIR R4 Bundle from FastAPI backend
  const handleLoadSample = async () => {
    setIsProcessing(true);
    setValidationErrors([]);
    setGeneralError(null);
    try {
      const sample = await fetchSampleFHIR();
      setJsonText(JSON.stringify(sample, null, 2));
      setFileName('sample_cardiometabolic_patient_fhir.json');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setGeneralError(`Failed to load sample record: ${msg}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Load an invalid sample to demonstrate clinical validation rejection
  const handleLoadInvalidSample = () => {
    const invalidSample = {
      resourceType: "Bundle",
      type: "collection",
      entry: [
        {
          resource: {
            resourceType: "Patient",
            id: "PT-ERR-TEST-09",
            gender: "female",
            birthDate: "1978-03-22"
          }
        },
        {
          resource: {
            resourceType: "Observation",
            id: "obs-err-hba1c",
            code: { coding: [{ system: "http://loinc.org", code: "4548-4", display: "HbA1c" }] },
            effectiveDateTime: "2026-01-15T09:00:00Z",
            valueQuantity: { value: 34.5, unit: "%" } // Exceeds physiological boundary of 25.0%
          }
        },
        {
          resource: {
            resourceType: "Observation",
            id: "obs-err-bp",
            code: { coding: [{ system: "http://loinc.org", code: "85354-9", display: "Blood pressure panel" }] },
            effectiveDateTime: "2026-01-15T09:00:00Z",
            component: [
              { code: { coding: [{ system: "http://loinc.org", code: "8480-6", display: "Systolic BP" }] }, valueQuantity: { value: 70, unit: "mmHg" } },
              { code: { coding: [{ system: "http://loinc.org", code: "8462-4", display: "Diastolic BP" }] }, valueQuantity: { value: 105, unit: "mmHg" } } // Inverted BP
            ]
          }
        }
      ]
    };
    setJsonText(JSON.stringify(invalidSample, null, 2));
    setFileName('invalid_physiological_test_sample.json');
    setValidationErrors([]);
    setGeneralError(null);
    setSuccessResponse(null);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setValidationErrors([]);
    setGeneralError(null);

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        // Verify valid JSON syntax
        JSON.parse(text);
        setJsonText(text);
      } catch {
        setGeneralError('File does not contain valid JSON syntax.');
      }
    };
    reader.readAsText(file);
  };

  const handleIngest = async () => {
    if (!jsonText.trim()) {
      setGeneralError('Please upload or load a FHIR JSON record first.');
      return;
    }

    setIsProcessing(true);
    setValidationErrors([]);
    setGeneralError(null);
    setSuccessResponse(null);

    let parsedPayload: unknown;
    try {
      parsedPayload = JSON.parse(jsonText);
    } catch {
      setGeneralError('Malformed JSON syntax. Please check formatting.');
      setIsProcessing(false);
      return;
    }

    try {
      // Direct ingestion against FastAPI backend
      const res = await ingestEMRPayload(parsedPayload);
      setSuccessResponse(res);
    } catch (err: unknown) {
      const errorObj = err as { status?: number; data?: { errors?: ClinicalValidationErrorItem[]; message?: string } };
      if (errorObj?.data?.errors && errorObj.data.errors.length > 0) {
        setValidationErrors(errorObj.data.errors);
      } else {
        const msg = err instanceof Error ? err.message : String(err);
        setGeneralError(msg || 'EMR ingestion rejected by clinical validation rules.');
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setJsonText('');
    setFileName(null);
    setValidationErrors([]);
    setGeneralError(null);
    setSuccessResponse(null);
  };

  return (
    <div className="space-y-6">
      {/* Upload & Import Action Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-slate-100">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 tracking-tight">
              Patient / EMR Ingestion Gateway
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Upload a de-identified FHIR R4 Bundle or test with real-world clinical records
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleLoadSample}
              disabled={isProcessing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-teal-800 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5 text-teal-600" />
              <span>Load Valid Sample</span>
            </button>

            <button
              onClick={handleLoadInvalidSample}
              disabled={isProcessing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
              title="Loads a test record with out-of-bounds values to test rejection"
            >
              <span>Test Invalid Record</span>
            </button>

            {(jsonText || successResponse) && (
              <button
                onClick={handleReset}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:text-slate-800 bg-slate-50 rounded-lg border border-slate-200 cursor-pointer"
                title="Reset view"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Upload Zone & Status */}
        <div className="mt-5 space-y-4">
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <label className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-300 rounded-lg cursor-pointer transition-colors shadow-2xs">
              <FileUp className="w-4 h-4 text-slate-500" />
              <span>Select FHIR JSON File</span>
              <input
                type="file"
                accept=".json,application/json"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>

            {fileName && (
              <span className="text-xs font-mono text-slate-600 bg-slate-100 px-2.5 py-1.5 rounded border border-slate-200">
                {fileName}
              </span>
            )}

            <button
              onClick={handleIngest}
              disabled={!jsonText || isProcessing}
              className="w-full sm:w-auto sm:ml-auto inline-flex items-center justify-center gap-2 px-5 py-2 text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 disabled:opacity-50 rounded-lg shadow-xs transition-colors cursor-pointer"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{isProcessing ? 'Validating & Ingesting...' : 'Validate & Ingest EMR'}</span>
            </button>
          </div>

          {/* Collapsible Raw JSON Inspector */}
          {jsonText && (
            <div className="pt-2">
              <button
                onClick={() => setShowRawJson(!showRawJson)}
                className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 font-medium cursor-pointer"
              >
                {showRawJson ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                <span>{showRawJson ? 'Hide Raw FHIR Payload' : 'Inspect Raw FHIR JSON'}</span>
              </button>

              {showRawJson && (
                <textarea
                  value={jsonText}
                  onChange={(e) => setJsonText(e.target.value)}
                  rows={8}
                  className="w-full mt-2 font-mono text-[11px] p-3 rounded-lg border border-slate-300 bg-slate-900 text-slate-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  spellCheck={false}
                />
              )}
            </div>
          )}
        </div>
      </div>

      {/* Validation Rejection Alert */}
      {validationErrors.length > 0 && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-5 text-rose-950 shadow-xs">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-xs font-bold text-rose-900 uppercase tracking-wider">
                Clinical Validation Rejected • Physiological or Boundary Violation
              </h3>
              <p className="text-xs text-rose-800 mt-0.5">
                The incoming medical record was rejected because {validationErrors.length} clinical or physiological constraints were violated:
              </p>

              <div className="mt-3 space-y-2">
                {validationErrors.map((err, i) => (
                  <div key={i} className="text-xs p-2.5 rounded-lg bg-white border border-rose-200 text-rose-900 space-y-0.5">
                    <div className="flex items-center justify-between font-semibold">
                      <span>{err.field}</span>
                      <span className="font-mono text-[10px] text-rose-600 uppercase bg-rose-100/70 px-1.5 py-0.5 rounded">
                        {err.code}
                      </span>
                    </div>
                    <p className="text-[11px] text-rose-800">{err.issue}</p>
                    {err.acceptable_range && (
                      <div className="text-[11px] font-mono text-slate-600">
                        Expected clinical bounds: <strong>{err.acceptable_range}</strong>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* General Error Message */}
      {generalError && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-900 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>{generalError}</span>
        </div>
      )}

      {/* Validated Ingested Patient Information View */}
      {successResponse && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-6">
          {/* Header & Demographics Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <h3 className="text-base font-bold text-slate-900">
                  Patient EMR Validated & Ingested
                </h3>
                <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                  {successResponse.patient_record.patient_id}
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                {successResponse.patient_record.age_years && (
                  <span>Age: <strong>{successResponse.patient_record.age_years} yrs</strong></span>
                )}
                {successResponse.patient_record.gender && (
                  <span>Sex: <strong className="capitalize">{successResponse.patient_record.gender}</strong></span>
                )}
                <span>Measurements: <strong>{successResponse.patient_record.total_biomarker_measurements}</strong></span>
                <span>Conditions: <strong>{successResponse.patient_record.conditions.length}</strong></span>
              </div>
            </div>

            {/* Audit Status Pill */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 self-start sm:self-center">
              <ShieldCheck className="w-4 h-4 text-teal-600" />
              <span>Audit ID: <strong className="font-mono text-[11px]">{successResponse.audit_event_id.slice(0, 8)}...</strong></span>
            </div>
          </div>

          {/* 4 Disease Domain Data Readiness Check */}
          <div>
            <h4 className="text-xs font-semibold text-slate-800 mb-2">
              Clinical Disease Data Readiness Check
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { key: 'diabetes', label: 'Diabetes Mellitus' },
                { key: 'cardiovascular', label: 'Cardiovascular' },
                { key: 'chronic_kidney_disease', label: 'Kidney Disease (CKD)' },
                { key: 'cancer', label: 'Oncology Early Detection' },
              ].map((domain) => {
                const isReady = successResponse.patient_record.clinical_domain_readiness[domain.key as keyof typeof successResponse.patient_record.clinical_domain_readiness];
                return (
                  <div
                    key={domain.key}
                    className={`p-2.5 rounded-lg border text-xs flex items-center justify-between ${
                      isReady
                        ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                        : 'bg-slate-50 border-slate-200 text-slate-500'
                    }`}
                  >
                    <span className="font-medium text-[11px]">{domain.label}</span>
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                      isReady ? 'bg-emerald-200 text-emerald-900' : 'bg-slate-200 text-slate-600'
                    }`}>
                      {isReady ? 'Ready' : 'Pending'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Longitudinal Biomarkers Timeline */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-teal-700" />
              <h4 className="text-xs font-semibold text-slate-900">
                Longitudinal Biomarkers & Physiological Measurements
              </h4>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Object.entries(successResponse.patient_record.longitudinal_biomarkers).map(([key, points]) => {
                const latest = points[points.length - 1];
                return (
                  <div key={key} className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/60 text-xs">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-semibold text-slate-900">{latest.standard_name}</span>
                      {latest.loinc_code && (
                        <span className="font-mono text-[10px] bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-500">
                          LOINC {latest.loinc_code}
                        </span>
                      )}
                    </div>

                    {/* Timeline Sequence */}
                    <div className="space-y-1 mt-2">
                      {points.map((pt, pIdx) => (
                        <div key={pIdx} className="flex items-center justify-between py-1 border-t border-slate-200/60 first:border-0 text-[11px]">
                          <span className="text-slate-500 flex items-center gap-1 font-mono">
                            <Calendar className="w-3 h-3 text-slate-400" />
                            {pt.effective_datetime.slice(0, 10)}
                          </span>
                          <span className="font-semibold text-slate-900">
                            {pt.value} <span className="font-normal text-slate-500">{pt.unit}</span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Conditions & Medications Split */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-slate-100">
            {/* Active Conditions */}
            <div>
              <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-slate-900">
                <Stethoscope className="w-4 h-4 text-slate-600" />
                <span>Documented Clinical Conditions</span>
              </div>
              <div className="space-y-1.5">
                {successResponse.patient_record.conditions.map((cond) => (
                  <div key={cond.condition_id} className="p-2.5 rounded bg-slate-50 border border-slate-200 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-medium text-slate-800 block">{cond.display_name}</span>
                      {cond.recorded_date && (
                        <span className="text-[10px] text-slate-500 font-mono">Onset: {cond.recorded_date}</span>
                      )}
                    </div>
                    <span className="font-mono text-[10px] font-semibold bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">
                      {cond.icd10_code}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Active Medications */}
            <div>
              <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-slate-900">
                <Pill className="w-4 h-4 text-slate-600" />
                <span>Active Pharmacotherapy</span>
              </div>
              <div className="space-y-1.5">
                {successResponse.patient_record.medications.map((med) => (
                  <div key={med.medication_id} className="p-2.5 rounded bg-slate-50 border border-slate-200 text-xs">
                    <div className="font-medium text-slate-800">{med.display_name}</div>
                    {med.dosage_instruction && (
                      <div className="text-[11px] text-slate-500 mt-0.5">{med.dosage_instruction}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Clinical Notes Preview */}
          {successResponse.patient_record.clinical_notes.length > 0 && (
            <div className="pt-3 border-t border-slate-100">
              <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-slate-900">
                <FileText className="w-4 h-4 text-slate-600" />
                <span>De-Identified Clinical Progress Notes</span>
              </div>
              <div className="space-y-2">
                {successResponse.patient_record.clinical_notes.map((note) => (
                  <div key={note.note_id} className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                    <div className="flex items-center justify-between mb-1 font-semibold text-slate-800 text-[11px]">
                      <span>{note.note_type}</span>
                      <span className="text-slate-400 font-mono">{note.created_at.slice(0, 10)}</span>
                    </div>
                    <p className="text-[11px] text-slate-600 leading-relaxed italic">
                      "{note.text_preview}"
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step 3: Disease Risk Stratification Review (Multi-Pathway Active) */}
          <div className="pt-4 border-t border-slate-200 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Step 3 • Disease Risk Stratification Pathways
                </span>
                <span className="text-[10px] font-semibold bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded border border-emerald-200">
                  2 Pathways Active
                </span>
              </div>

              {/* Pathway Switcher Tabs */}
              <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs self-start sm:self-center">
                <button
                  onClick={() => setSelectedRiskDomain('diabetes')}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                    selectedRiskDomain === 'diabetes'
                      ? 'bg-white text-teal-900 font-semibold shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Type 2 Diabetes
                </button>
                <button
                  onClick={() => setSelectedRiskDomain('cardiovascular')}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                    selectedRiskDomain === 'cardiovascular'
                      ? 'bg-white text-teal-900 font-semibold shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Cardiovascular (ASCVD)
                </button>
              </div>
            </div>

            {selectedRiskDomain === 'diabetes' ? (
              <DiabetesRiskReviewView patientId={successResponse.patient_record.patient_id} />
            ) : (
              <CardiovascularRiskReviewView patientId={successResponse.patient_record.patient_id} />
            )}
          </div>
        </div>
      )}
    </div>
  );
};
