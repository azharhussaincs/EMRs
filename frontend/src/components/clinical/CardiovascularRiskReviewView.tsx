'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  HeartPulse,
  AlertCircle,
  Clock,
  Info,
  Layers,
  RotateCcw,
  ShieldAlert,
  SlidersHorizontal,
  CheckCircle2,
  FileText,
  AlertTriangle,
} from 'lucide-react';
import {
  fetchPatientCardiovascularRisk,
  fetchCardiovascularModelCard,
} from '@/lib/api';
import type {
  RiskAssessmentResult,
  ModelGovernanceCard,
  DataSufficiencyStatus,
} from '@/types/clinical';
import { ClinicalNarrativeView } from './ClinicalNarrativeView';
import { ClinicalEvidenceReviewView } from './ClinicalEvidenceReviewView';

interface CardiovascularRiskReviewViewProps {
  patientId: string;
  autoFetch?: boolean;
}

export const CardiovascularRiskReviewView: React.FC<CardiovascularRiskReviewViewProps> = ({
  patientId,
  autoFetch = true,
}) => {
  const [assessment, setAssessment] = useState<RiskAssessmentResult | null>(null);
  const [modelCard, setModelCard] = useState<ModelGovernanceCard | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showGovernance, setShowGovernance] = useState<boolean>(false);
  const [governanceLoading, setGovernanceLoading] = useState<boolean>(false);

  const loadAssessment = useCallback(async () => {
    if (!patientId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchPatientCardiovascularRisk(patientId);
      setAssessment(res);
    } catch (err: unknown) {
      const errObj = err as Error & { status?: number };
      const msg = errObj?.message || 'Failed to retrieve cardiovascular risk assessment.';
      if (errObj?.status === 404) {
        setError(
          `Patient record for '${patientId}' was not found in the clinical repository. Please ingest the EMR first.`
        );
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    if (autoFetch && patientId) {
      loadAssessment();
    }
  }, [autoFetch, patientId, loadAssessment]);

  const toggleGovernanceCard = async () => {
    if (!showGovernance && !modelCard) {
      setGovernanceLoading(true);
      try {
        const card = await fetchCardiovascularModelCard();
        setModelCard(card);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setError(`Failed to retrieve cardiovascular model governance card: ${msg}`);
      } finally {
        setGovernanceLoading(false);
      }
    }
    setShowGovernance((prev) => !prev);
  };

  const formatSufficiencyBadge = (status: DataSufficiencyStatus) => {
    switch (status) {
      case 'sufficient_data':
        return {
          label: 'Sufficient Risk Factor History',
          badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-200',
          dotClass: 'bg-emerald-500',
          detail: 'All 7 core ASCVD clinical inputs documented in EMR without imputation',
        };
      case 'insufficient_data':
        return {
          label: 'Insufficient Clinical Data',
          badgeClass: 'bg-amber-50 text-amber-800 border-amber-200',
          dotClass: 'bg-amber-500',
          detail: 'Incomplete ASCVD factor profile; missing values preserved without imputation',
        };
      case 'unavailable_feature':
      default:
        return {
          label: 'Cardiovascular Features Unavailable',
          badgeClass: 'bg-slate-100 text-slate-700 border-slate-300',
          dotClass: 'bg-slate-400',
          detail: 'Baseline blood pressure and lipid panel observations missing from EMR',
        };
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <HeartPulse className="w-4 h-4 text-rose-600" />
            <h3 className="text-sm font-semibold text-slate-900 tracking-tight">
              Clinical Risk Stratification • Cardiovascular Disease (ASCVD)
            </h3>
            <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
              {patientId}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Atherosclerotic cardiovascular disease (ASCVD) risk factor profile & blood pressure trajectory
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleGovernanceCard}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors cursor-pointer"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
            <span>{showGovernance ? 'Hide Governance' : 'Model Governance'}</span>
          </button>

          <button
            onClick={loadAssessment}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-teal-800 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>{isLoading ? 'Assessing...' : 'Refresh Assessment'}</span>
          </button>
        </div>
      </div>

      {/* Model Governance Panel (Collapsible) */}
      {showGovernance && (
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-900">
              <Layers className="w-3.5 h-3.5 text-teal-700" />
              <span>Cardiovascular Model Governance Specification</span>
            </div>
            {modelCard && (
              <span className="text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600">
                {modelCard.version}
              </span>
            )}
          </div>

          {governanceLoading && (
            <p className="text-xs text-slate-500">Loading model governance card...</p>
          )}

          {modelCard && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 rounded bg-white border border-slate-200 space-y-1">
                <span className="text-slate-500 text-[11px] block">Estimator Pipeline</span>
                <span className="font-mono text-slate-800 font-semibold">{modelCard.estimator_id}</span>
              </div>
              <div className="p-2.5 rounded bg-white border border-slate-200 space-y-1">
                <span className="text-slate-500 text-[11px] block">Calibration State</span>
                <span className="font-semibold text-amber-800 capitalize">{modelCard.calibration_status.replace('_', ' ')}</span>
              </div>
              <div className="p-2.5 rounded bg-white border border-slate-200 space-y-1 sm:col-span-2">
                <span className="text-slate-500 text-[11px] block">Intended Clinical Input Features</span>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {modelCard.input_features.map((feat) => (
                    <span key={feat} className="font-mono text-[10px] bg-slate-100 px-2 py-0.5 rounded text-slate-700">
                      {feat}
                    </span>
                  ))}
                </div>
              </div>
              <div className="p-2.5 rounded bg-white border border-slate-200 space-y-1 sm:col-span-2">
                <span className="text-slate-500 text-[11px] block">Core Cohort Assumptions</span>
                <p className="text-slate-700 text-[11px] leading-relaxed">{modelCard.assumptions}</p>
              </div>
              <div className="p-2.5 rounded bg-white border border-slate-200 space-y-1 sm:col-span-2">
                <span className="text-slate-500 text-[11px] block">Regulatory & Decision Boundary</span>
                <p className="text-slate-700 text-[11px] leading-relaxed italic">{modelCard.disclaimer}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-900 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading && !assessment && (
        <div className="py-8 text-center text-xs text-slate-500 space-y-2">
          <div className="inline-block w-5 h-5 border-2 border-teal-600 border-t-transparent rounded-full animate-spin" />
          <p>Evaluating cardiovascular risk factors against clinical constraints...</p>
        </div>
      )}

      {/* Assessment Body */}
      {assessment && (
        <div className="space-y-6">
          {/* Top Status & Statistical Safety Banner */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Data Sufficiency Badge */}
            {(() => {
              const badge = formatSufficiencyBadge(assessment.data_sufficiency);
              return (
                <div className={`p-3.5 rounded-xl border text-xs space-y-1 ${badge.badgeClass}`}>
                  <div className="flex items-center gap-2 font-semibold">
                    <span className={`w-2 h-2 rounded-full ${badge.dotClass}`} />
                    <span>{badge.label}</span>
                  </div>
                  <p className="text-[11px] opacity-90">{badge.detail}</p>
                </div>
              );
            })()}

            {/* Calibration Safety Callout (Probability Withheld) */}
            <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 text-xs space-y-1">
              <div className="flex items-center justify-between font-semibold text-slate-800">
                <span className="flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5 text-slate-500" />
                  <span>10-Year ASCVD Risk Probability</span>
                </span>
                <span className="text-[10px] font-mono uppercase bg-slate-200 px-1.5 py-0.5 rounded text-slate-700">
                  {assessment.calibration_status.replace('_', ' ')}
                </span>
              </div>
              <p className="text-[11px] text-slate-600 leading-relaxed">
                Empirical ASCVD probability is strictly withheld. The estimator is in research foundation phase (v0.1.0-foundation); no fabricated numerical risk percentage or heuristic score is emitted.
              </p>
            </div>
          </div>

          {/* Core ASCVD Risk Factors Grid (7 Factors) */}
          <div>
            <h4 className="text-xs font-semibold text-slate-900 mb-3 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-slate-500" />
              <span>Extracted ASCVD Clinical Risk Factors & Biomarkers</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {/* 1. Systolic Blood Pressure */}
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 block">Systolic BP</span>
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                    Hemodynamics
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-900">
                  {assessment.features_used.systolic_bp?.value !== undefined && assessment.features_used.systolic_bp?.value !== null
                    ? `${assessment.features_used.systolic_bp.value} ${assessment.features_used.systolic_bp.unit || 'mmHg'}`
                    : 'Unavailable'}
                </div>
                {assessment.features_used.systolic_bp?.source_timestamp && (
                  <span className="text-[10px] text-slate-400 font-mono block">
                    {assessment.features_used.systolic_bp.source_timestamp.slice(0, 10)}
                  </span>
                )}
              </div>

              {/* 2. Total Serum Cholesterol */}
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 block">Total Cholesterol</span>
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                    Lipid Panel
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-900">
                  {assessment.features_used.total_cholesterol?.value !== undefined && assessment.features_used.total_cholesterol?.value !== null
                    ? `${assessment.features_used.total_cholesterol.value} ${assessment.features_used.total_cholesterol.unit || 'mg/dL'}`
                    : 'Unavailable'}
                </div>
                {assessment.features_used.total_cholesterol?.source_timestamp ? (
                  <span className="text-[10px] text-slate-400 font-mono block">
                    {assessment.features_used.total_cholesterol.source_timestamp.slice(0, 10)}
                  </span>
                ) : (
                  <span className="text-[10px] text-amber-700 block">Not measured</span>
                )}
              </div>

              {/* 3. HDL Cholesterol */}
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 block">HDL Cholesterol</span>
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                    Cardioprotective
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-900">
                  {assessment.features_used.hdl_cholesterol?.value !== undefined && assessment.features_used.hdl_cholesterol?.value !== null
                    ? `${assessment.features_used.hdl_cholesterol.value} ${assessment.features_used.hdl_cholesterol.unit || 'mg/dL'}`
                    : 'Unavailable'}
                </div>
                {assessment.features_used.hdl_cholesterol?.source_timestamp ? (
                  <span className="text-[10px] text-slate-400 font-mono block">
                    {assessment.features_used.hdl_cholesterol.source_timestamp.slice(0, 10)}
                  </span>
                ) : (
                  <span className="text-[10px] text-amber-700 block">Not measured</span>
                )}
              </div>

              {/* 4. Smoking Status */}
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 block">Smoking Status</span>
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                    Behavioral
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-900">
                  {assessment.features_used.smoking_status
                    ? assessment.features_used.smoking_status.description.replace('Smoking status: ', '')
                    : 'Undocumented'}
                </div>
                <span className="text-[10px] text-slate-400 block">
                  {assessment.features_used.smoking_status ? 'Verified in conditions' : 'No tobacco code recorded'}
                </span>
              </div>

              {/* 5. Diabetes Status */}
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 block">Diabetes Status</span>
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                    Metabolic
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-900">
                  {assessment.features_used.diabetes_status
                    ? assessment.features_used.diabetes_status.description
                    : 'Undocumented'}
                </div>
                <span className="text-[10px] text-slate-400 block">
                  {assessment.features_used.diabetes_status ? 'Cross-domain linkage' : 'Absence of diabetes criteria'}
                </span>
              </div>

              {/* 6. Chronological Age */}
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 block">Patient Age</span>
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                    Demographic
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-900">
                  {assessment.features_used.age?.value !== undefined && assessment.features_used.age?.value !== null
                    ? `${assessment.features_used.age.value} years`
                    : 'Unavailable'}
                </div>
                <span className="text-[10px] text-slate-400 block">Derived from birth date</span>
              </div>

              {/* 7. Administrative Sex */}
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 block">Administrative Sex</span>
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                    Demographic
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-900 capitalize">
                  {assessment.features_used.gender
                    ? assessment.features_used.gender.description.replace('Administrative sex: ', '')
                    : 'Unavailable'}
                </div>
                <span className="text-[10px] text-slate-400 block">Biological baseline</span>
              </div>
            </div>
          </div>

          {/* Unavailable Inputs Notification (if any) */}
          {assessment.unavailable_inputs.length > 0 && (
            <div className="p-4 rounded-xl bg-amber-50/60 border border-amber-200 text-xs space-y-2">
              <div className="flex items-center gap-1.5 font-semibold text-amber-900">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>
                  Missing Required ASCVD Parameters ({assessment.unavailable_inputs.length})
                </span>
              </div>
              <p className="text-[11px] text-amber-800 leading-relaxed">
                The following clinical inputs are required by standard ASCVD calculators but are absent from the patient&rsquo;s medical record. In accordance with clinical safety principles, missing parameters are explicitly displayed rather than statistically imputed:
              </p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {assessment.unavailable_inputs.map((inp) => (
                  <span
                    key={inp}
                    className="font-mono text-[10px] bg-white border border-amber-300 text-amber-900 px-2 py-0.5 rounded font-semibold"
                  >
                    {inp}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Limitations and Model Assumptions */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-700 font-semibold">
              <span>Estimator Limitations & Constraints</span>
              <span className="text-[10px] font-mono text-slate-500">
                {assessment.estimator_id} ({assessment.estimator_version})
              </span>
            </div>
            <ul className="space-y-1 text-[11px] text-slate-600 list-disc list-inside">
              {assessment.limitations.map((lim, idx) => (
                <li key={idx} className="leading-relaxed">{lim}</li>
              ))}
            </ul>
          </div>

          {/* Metadata & Timestamp */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[11px] text-slate-500 pt-2 border-t border-slate-100">
            <span className="flex items-center gap-1 font-mono">
              <Clock className="w-3 h-3 text-slate-400" />
              Assessed: {new Date(assessment.assessed_at).toUTCString()}
            </span>
            <span className="font-mono text-[10px]">
              Assessment ID: {assessment.assessment_id}
            </span>
          </div>

          {/* Mandatory Clinical Disclaimer */}
          <div className="p-3 rounded-lg bg-slate-100/70 border border-slate-200 text-[11px] text-slate-600 leading-relaxed flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
            <span>
              <strong>Clinical Decision Boundary:</strong> {assessment.disclaimer}
            </span>
          </div>

          {/* Step 4: AI Clinical Explanation Section */}
          <div className="pt-2 border-t border-slate-100">
            <ClinicalNarrativeView patientId={patientId} domain="cardiovascular" />
          </div>

          {/* Step 5: Supporting Evidence & Clinical Guidelines Review */}
          <div className="pt-2 border-t border-slate-100">
            <ClinicalEvidenceReviewView patientId={patientId} domain="cardiovascular" />
          </div>
        </div>
      )}
    </div>
  );
};
