'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { WorkflowStepper } from '@/components/clinical/WorkflowStepper';
import { DomainOverview } from '@/components/clinical/DomainOverview';
import { EMRIngestionView } from '@/components/clinical/EMRIngestionView';
import { fetchHealthStatus, fetchClinicalDomains } from '@/lib/api';
import type { HealthCheckResponse, DiseaseDomainRegistryEntry } from '@/types/clinical';
import { ArrowRight, CheckCircle2 } from 'lucide-react';

const FALLBACK_DOMAINS: DiseaseDomainRegistryEntry[] = [
  {
    domain: 'diabetes',
    display_name: 'Type 2 Diabetes Mellitus & Complications',
    icd10_family: ['E11', 'E11.9', 'E11.65'],
    snomed_ct_concept: '44054006',
    description: 'Assessment of glycemic trajectory, conversion from prediabetes, and microvascular complication risk.',
    primary_biomarkers: [
      { name: 'Hemoglobin A1c', loinc_code: '4548-4', unit: '%', description: 'Glycated hemoglobin index' },
      { name: 'Fasting Plasma Glucose', loinc_code: '1558-6', unit: 'mg/dL', description: 'Fasting glycemic measurement' },
      { name: 'Body Mass Index', loinc_code: '39156-5', unit: 'kg/m²', description: 'Anthropometric obesity metric' },
    ],
    consensus_guidelines: [
      {
        organization: 'American Diabetes Association (ADA)',
        title: 'Standards of Care in Diabetes',
        edition_year: 2024,
        evidence_level: 'Level A',
      },
    ],
    target_risk_horizons: ['3-year', '5-year', '10-year'],
  },
  {
    domain: 'cardiovascular',
    display_name: 'Cardiovascular Disease (ASCVD & Heart Failure)',
    icd10_family: ['I25.10', 'I21.9', 'I50.9'],
    snomed_ct_concept: '49436004',
    description: 'Assessment of 10-year primary ASCVD event risk (myocardial infarction, stroke) and decompensated heart failure.',
    primary_biomarkers: [
      { name: 'Systolic Blood Pressure', loinc_code: '8480-6', unit: 'mmHg', description: 'Resting systolic arterial pressure' },
      { name: 'Total Cholesterol', loinc_code: '2093-3', unit: 'mg/dL', description: 'Total serum cholesterol' },
      { name: 'HDL Cholesterol', loinc_code: '2085-9', unit: 'mg/dL', description: 'High-density lipoprotein cholesterol' },
    ],
    consensus_guidelines: [
      {
        organization: 'American College of Cardiology / AHA',
        title: 'Guideline on Primary Prevention of Cardiovascular Disease',
        edition_year: 2019,
        evidence_level: 'Class I / Level A',
      },
    ],
    target_risk_horizons: ['5-year', '10-year'],
  },
  {
    domain: 'chronic_kidney_disease',
    display_name: 'Chronic Kidney Disease (CKD) Progression',
    icd10_family: ['N18.1', 'N18.3', 'N18.5'],
    snomed_ct_concept: '709044004',
    description: 'Progression across KDIGO G1-G5 staging, annual eGFR trajectory, and risk of End-Stage Renal Disease.',
    primary_biomarkers: [
      { name: 'eGFR (CKD-EPI)', loinc_code: '33914-3', unit: 'mL/min/1.73m²', description: 'Filtered creatinine indicator' },
      { name: 'Urine Albumin-Creatinine Ratio', loinc_code: '14959-1', unit: 'mg/g', description: 'Renal microalbuminuria marker' },
      { name: 'Serum Creatinine', loinc_code: '2160-0', unit: 'mg/dL', description: 'Metabolic kidney byproduct' },
    ],
    consensus_guidelines: [
      {
        organization: 'Kidney Disease: Improving Global Outcomes (KDIGO)',
        title: 'Clinical Practice Guideline for CKD Evaluation & Management',
        edition_year: 2024,
        evidence_level: 'Grade 1A',
      },
    ],
    target_risk_horizons: ['1-year', '2-year', '5-year'],
  },
  {
    domain: 'cancer',
    display_name: 'Oncology Early Detection & Screening',
    icd10_family: ['C00-D49', 'C34.90', 'C50.919'],
    snomed_ct_concept: '363346000',
    description: 'Evaluation of clinical suspicion, hereditary predisposition, and screening protocol adherence across solid tumors.',
    primary_biomarkers: [
      { name: 'Carcinoembryonic Antigen (CEA)', loinc_code: '2039-6', unit: 'ng/mL', description: 'Colorectal epithelial marker' },
      { name: 'Prostate-Specific Antigen (PSA)', loinc_code: '2857-1', unit: 'ng/mL', description: 'Prostate malignancy marker' },
      { name: 'CA-125', loinc_code: '10334-1', unit: 'U/mL', description: 'Adnexal/ovarian tumor marker' },
    ],
    consensus_guidelines: [
      {
        organization: 'National Comprehensive Cancer Network (NCCN)',
        title: 'Guidelines in Oncology: Detection, Prevention & Risk',
        edition_year: 2024,
        evidence_level: 'Category 1',
      },
    ],
    target_risk_horizons: ['1-year', '5-year'],
  },
];

export default function Home() {
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [domains, setDomains] = useState<DiseaseDomainRegistryEntry[]>(FALLBACK_DOMAINS);
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const healthRes = await fetchHealthStatus();
        setHealth(healthRes);
        setIsBackendConnected(true);

        const domainRes = await fetchClinicalDomains();
        if (domainRes && domainRes.length > 0) {
          setDomains(domainRes);
        }
      } catch {
        setIsBackendConnected(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Top Header */}
      <Header isBackendConnected={isBackendConnected} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 space-y-8">
        {/* Platform Overview Banner */}
        <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold uppercase tracking-wider mb-2">
                Phase 4 • EMR Ingestion, Risk Stratification, AI Narrative & Supporting Evidence Active
              </div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                Generative AI-Based Clinical Risk Assessment Using EMR
              </h1>
              <p className="text-xs text-slate-600 mt-1 max-w-3xl leading-relaxed">
                Ingest standardized, de-identified FHIR R4 medical records, extract longitudinal biomarker trajectories, assess clinical risk stratification, synthesize strictly grounded clinical explanations, and review verified clinical practice guidelines.
              </p>
            </div>

            {/* Linear Workflow Pill */}
            <div className="hidden lg:flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700 shrink-0">
              <span className="text-teal-800 font-semibold bg-teal-50 px-2 py-0.5 rounded border border-teal-200">1. EMR Ingestion</span>
              <ArrowRight className="w-3 h-3 text-slate-400" />
              <span className="text-teal-800 font-semibold bg-teal-50 px-2 py-0.5 rounded border border-teal-200">2. Clinical Info</span>
              <ArrowRight className="w-3 h-3 text-slate-400" />
              <span className="text-teal-800 font-semibold bg-teal-50 px-2 py-0.5 rounded border border-teal-200">3. Risk (DM & CVD)</span>
              <ArrowRight className="w-3 h-3 text-slate-400" />
              <span className="text-teal-800 font-semibold bg-teal-50 px-2 py-0.5 rounded border border-teal-200">4. AI Explanation</span>
              <ArrowRight className="w-3 h-3 text-slate-400" />
              <span className="text-teal-800 font-semibold bg-teal-50 px-2 py-0.5 rounded border border-teal-200">5. Evidence</span>
            </div>
          </div>
        </section>

        {/* 1. Clinical Ingestion & Inspection Screen */}
        <section>
          <EMRIngestionView />
        </section>

        {/* 2. Clinical Decision Support Workflow Stepper */}
        <section>
          <WorkflowStepper />
        </section>

        {/* 3. Target Disease Domains */}
        <section>
          <DomainOverview domains={domains} />
        </section>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}
