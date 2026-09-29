'use client';

import React, { useState } from 'react';
import {
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Info,
  Layers,
  RotateCcw,
  FileText,
  AlertTriangle,
  Cpu,
} from 'lucide-react';
import {
  generatePatientDiabetesNarrative,
  generatePatientCardiovascularNarrative,
} from '@/lib/api';
import type { ClinicalNarrativeExplanation, ClinicalDomain } from '@/types/clinical';

interface ClinicalNarrativeViewProps {
  patientId: string;
  domain?: ClinicalDomain;
}

export const ClinicalNarrativeView: React.FC<ClinicalNarrativeViewProps> = ({
  patientId,
  domain = 'diabetes',
}) => {
  const [narrative, setNarrative] = useState<ClinicalNarrativeExplanation | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<
    'provider_not_configured' | 'validation_failure' | 'general' | null
  >(null);

  const isCardiovascular = domain === 'cardiovascular';

  const handleGenerateNarrative = async () => {
    if (!patientId) return;

    setIsGenerating(true);
    setError(null);
    setErrorType(null);

    try {
      const result = isCardiovascular
        ? await generatePatientCardiovascularNarrative(patientId)
        : await generatePatientDiabetesNarrative(patientId);
      setNarrative(result);
    } catch (err: unknown) {
      const errObj = err as Error & { status?: number };
      const msg = errObj?.message || 'Failed to generate clinical explanation narrative.';

      if (errObj?.status === 503 || msg.toLowerCase().includes('not configured')) {
        setErrorType('provider_not_configured');
        setError(
          'Generative AI provider is not configured with an active API key in this environment. Narrative synthesis is safely withheld.'
        );
      } else if (errObj?.status === 502 || msg.toLowerCase().includes('validation rejected')) {
        setErrorType('validation_failure');
        setError(
          'Clinical Safety Guard: AI generation was rejected because the output did not strictly conform to verified clinical safety boundaries.'
        );
      } else if (errObj?.status === 404) {
        setErrorType('general');
        setError(
          `Patient record for '${patientId}' was not found in the clinical repository. Please ingest the EMR first.`
        );
      } else {
        setErrorType('general');
        setError(msg);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-5">
      {/* Header & Trigger */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-teal-700" />
            <h3 className="text-sm font-semibold text-slate-900 tracking-tight">
              {isCardiovascular
                ? 'AI Clinical Risk Explanation • Cardiovascular (ASCVD)'
                : 'AI Clinical Risk Explanation • Step 4'}
            </h3>
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200">
              Grounded Narrative
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {isCardiovascular
              ? 'Controlled, risk-factor-grounded synthesis derived strictly from verified ASCVD clinical features'
              : 'Controlled, trajectory-grounded synthesis derived strictly from verified clinical features'}
          </p>
        </div>

        <div>
          <button
            onClick={handleGenerateNarrative}
            disabled={isGenerating}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 disabled:opacity-50 rounded-lg shadow-2xs transition-colors cursor-pointer"
          >
            {isGenerating ? (
              <>
                <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                <span>Synthesizing Narrative...</span>
              </>
            ) : narrative ? (
              <>
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Re-synthesize Narrative</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Synthesize Clinical Narrative</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Loading State */}
      {isGenerating && (
        <div className="py-8 text-center text-xs text-slate-500 space-y-2">
          <div className="inline-block w-5 h-5 border-2 border-teal-600 border-t-transparent rounded-full animate-spin" />
          <p className="font-medium text-slate-700">Synthesizing factual clinical explanation narrative...</p>
          <p className="text-[11px] text-slate-400">
            {isCardiovascular
              ? 'Grounding exclusively on verified blood pressure and lipid risk profile without external hallucinations'
              : 'Grounding exclusively on verified HbA1c trajectory without external hallucinations'}
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !isGenerating && (
        <div
          className={`p-4 rounded-xl border text-xs space-y-1.5 ${
            errorType === 'provider_not_configured'
              ? 'bg-slate-50 border-slate-300 text-slate-800'
              : errorType === 'validation_failure'
              ? 'bg-rose-50 border-rose-200 text-rose-950'
              : 'bg-amber-50 border-amber-200 text-amber-950'
          }`}
        >
          <div className="flex items-center gap-2 font-semibold">
            {errorType === 'provider_not_configured' ? (
              <Cpu className="w-4 h-4 text-slate-600 shrink-0" />
            ) : errorType === 'validation_failure' ? (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            )}
            <span>
              {errorType === 'provider_not_configured'
                ? 'LLM Provider Configuration Required'
                : errorType === 'validation_failure'
                ? 'Clinical Safety Rejection'
                : 'Narrative Synthesis Unavailable'}
            </span>
          </div>
          <p className="text-[11px] leading-relaxed opacity-90">{error}</p>
        </div>
      )}

      {/* Narrative Initial Placeholder State */}
      {!narrative && !isGenerating && !error && (
        <div className="p-4 rounded-xl border border-dashed border-slate-200 bg-slate-50/50 text-center text-xs text-slate-500 space-y-1">
          <FileText className="w-5 h-5 text-slate-400 mx-auto" />
          <p className="font-medium text-slate-700">Clinical Narrative Not Yet Synthesized</p>
          <p className="text-[11px] text-slate-400 max-w-lg mx-auto">
            {isCardiovascular
              ? 'Click “Synthesize Clinical Narrative” to generate a strictly grounded, non-diagnostic synthesis of the patient’s observed cardiovascular risk profile.'
              : 'Click “Synthesize Clinical Narrative” to generate a strictly grounded, non-diagnostic synthesis of the patient’s observed HbA1c trajectory.'}
          </p>
        </div>
      )}

      {/* Validated Narrative Content */}
      {narrative && !isGenerating && (
        <div className="space-y-4">
          {/* Section 1: Clinical Summary (AI Synthesis) */}
          <div className="p-4 rounded-xl bg-teal-50/40 border border-teal-200/70 text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-teal-950 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-teal-700" />
                <span>1. Clinical Summary</span>
              </span>
              <span className="text-[10px] font-semibold uppercase bg-teal-100/70 text-teal-800 px-2 py-0.5 rounded border border-teal-200">
                AI Narrative Synthesis
              </span>
            </div>
            <p className="text-[12px] text-teal-900 leading-relaxed font-medium">
              {narrative.summary}
            </p>
          </div>

          {/* Section 2: Observed Trajectory (Verified Facts) */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>{isCardiovascular ? '2. Observed Cardiovascular Profile / Trajectory' : '2. Observed Trajectory'}</span>
              </span>
              <span className="text-[10px] font-semibold uppercase bg-slate-200/80 text-slate-700 px-2 py-0.5 rounded border border-slate-300">
                Verified Clinical Facts
              </span>
            </div>
            <p className="text-[11px] text-slate-700 leading-relaxed">
              {narrative.observed_trajectory}
            </p>
          </div>

          {/* Section 3: Data Limitations (Quality & History Constraints) */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-900 flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-slate-500" />
                <span>3. Data Limitations</span>
              </span>
              <span className="text-[10px] font-semibold uppercase bg-slate-200/80 text-slate-700 px-2 py-0.5 rounded border border-slate-300">
                Completeness Constraints
              </span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              {narrative.data_limitations}
            </p>
          </div>

          {/* Section 4: Statistical Calibration Status (No Numerical Probability) */}
          <div className="p-4 rounded-xl bg-amber-50/40 border border-amber-200 text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-amber-950 flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                <span>4. Statistical Calibration Status</span>
              </span>
              <span className="text-[10px] font-semibold uppercase bg-amber-100 text-amber-900 px-2 py-0.5 rounded border border-amber-300">
                Probability Withheld
              </span>
            </div>
            <p className="text-[11px] text-amber-900 leading-relaxed">
              {narrative.statistical_calibration_status}
            </p>
          </div>

          {/* Section 5: Regulatory / Non-Diagnostic Disclaimer */}
          <div className="p-3.5 rounded-lg bg-slate-100/80 border border-slate-200 text-[11px] text-slate-600 leading-relaxed flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-800 block mb-0.5">
                5. Regulatory & Clinical Decision Boundary Disclaimer:
              </span>
              <span>{narrative.disclaimer}</span>
            </div>
          </div>

          {/* Traceability & Audit Metadata Footer */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[10px] text-slate-400 pt-2 border-t border-slate-100 font-mono">
            <span>
              Provider: <strong>{narrative.provider}</strong> ({narrative.model_name})
            </span>
            <span>Narrative ID: {narrative.narrative_id}</span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-300" />
              Generated: {new Date(narrative.generated_at).toUTCString()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
