'use client';

import React, { useState } from 'react';
import {
  FileText,
  Activity,
  BrainCircuit,
  Bot,
  BookOpen,
  ArrowRight,
  CheckCircle,
} from 'lucide-react';
import type { WorkflowStep } from '@/types/clinical';

const WORKFLOW_STEPS: WorkflowStep[] = [
  {
    id: 'emr',
    stepNumber: 1,
    label: 'Patient / EMR',
    summary: 'Electronic health record ingestion',
    detail:
      'Ingests standardized longitudinal medical records (FHIR R4 / HL7) containing demographics, vital signs, lab panels, and clinical progress notes while stripping direct identifiers for patient privacy.',
  },
  {
    id: 'clinical_info',
    stepNumber: 2,
    label: 'Clinical Information',
    summary: 'Biomarkers & diagnostic history',
    detail:
      'Normalizes continuous physiological biomarkers (HbA1c, eGFR, Blood Pressure, Lipid panels) and maps diagnostic histories (ICD-10 / SNOMED-CT) into structured longitudinal trajectories.',
  },
  {
    id: 'risk_assessment',
    stepNumber: 3,
    label: 'Risk Assessment',
    summary: 'Calibrated multi-disease scoring',
    detail:
      'Computes empirical risk probabilities and 95% confidence intervals across the 4 core disease areas: Diabetes, Cardiovascular Disease, Chronic Kidney Disease, and Cancer.',
  },
  {
    id: 'ai_explanation',
    stepNumber: 4,
    label: 'AI Explanation',
    summary: 'Dual-audience clinical narrative',
    detail:
      'Generates transparent pathophysiological rationales tailored for attending physicians and clear, accessible summaries for patient understanding, mitigating black-box opacity.',
  },
  {
    id: 'evidence',
    stepNumber: 5,
    label: 'Supporting Evidence',
    summary: 'Consensus guideline citations',
    detail:
      'Grounds every clinical insight in consensus practice guidelines from ADA, ACC/AHA, KDIGO, and NCCN, ensuring auditable, evidence-based clinician trust.',
  },
];

export const WorkflowStepper: React.FC = () => {
  const [activeStepId, setActiveStepId] = useState<string>('emr');

  const activeStep =
    WORKFLOW_STEPS.find((s) => s.id === activeStepId) || WORKFLOW_STEPS[0];

  const getStepIcon = (id: string) => {
    switch (id) {
      case 'emr':
        return FileText;
      case 'clinical_info':
        return Activity;
      case 'risk_assessment':
        return BrainCircuit;
      case 'ai_explanation':
        return Bot;
      case 'evidence':
      default:
        return BookOpen;
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
      {/* Title */}
      <div className="mb-5">
        <h2 className="text-sm font-semibold text-slate-900 tracking-tight">
          Clinical Decision Support Flow
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Linear, auditable progression from raw medical records to evidence-backed clinical action
        </p>
      </div>

      {/* Stepper Grid / Chain */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 pb-6 border-b border-slate-100">
        {WORKFLOW_STEPS.map((step, idx) => {
          const Icon = getStepIcon(step.id);
          const isSelected = activeStepId === step.id;

          return (
            <button
              key={step.id}
              onClick={() => setActiveStepId(step.id)}
              className={`relative flex flex-col items-start p-3 rounded-lg border text-left transition-all cursor-pointer ${
                isSelected
                  ? 'bg-teal-50/70 border-teal-500/80 shadow-xs'
                  : 'bg-slate-50 hover:bg-slate-100/80 border-slate-200/80 text-slate-600'
              }`}
            >
              <div className="flex items-center justify-between w-full mb-2">
                <span
                  className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-semibold ${
                    isSelected
                      ? 'bg-teal-600 text-white'
                      : 'bg-white text-slate-600 border border-slate-200'
                  }`}
                >
                  {step.stepNumber}
                </span>
                <Icon
                  className={`w-4 h-4 ${
                    isSelected ? 'text-teal-600' : 'text-slate-400'
                  }`}
                />
              </div>

              <span
                className={`text-xs font-semibold ${
                  isSelected ? 'text-teal-950' : 'text-slate-800'
                }`}
              >
                {step.label}
              </span>
              <span className="text-[11px] text-slate-500 mt-0.5 leading-snug">
                {step.summary}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active Step Explainer Card */}
      <div className="mt-5 p-4 rounded-lg bg-slate-50 border border-slate-200">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-teal-700 uppercase tracking-wider">
              Step {activeStep.stepNumber} of 5
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-xs font-semibold text-slate-900">
              {activeStep.label}
            </span>
          </div>
          <span className="text-[11px] text-slate-500 font-medium">
            Foundation Ready
          </span>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed">
          {activeStep.detail}
        </p>
      </div>
    </div>
  );
};
