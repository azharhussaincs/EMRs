'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  BookOpen,
  ExternalLink,
  RotateCcw,
  AlertCircle,
  CheckCircle2,
  ShieldCheck,
  Info,
  Layers,
  Clock,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  fetchPatientDiabetesEvidence,
  fetchPatientCardiovascularEvidence,
  fetchEvidenceSources,
} from '@/lib/api';
import type {
  EvidenceRetrievalResponse,
  ClinicalEvidenceReference,
  EvidenceSourceRegistryEntry,
  EvidenceDomainCategory,
  ClinicalDomain,
} from '@/types/clinical';

interface ClinicalEvidenceReviewViewProps {
  patientId: string;
  domain?: ClinicalDomain;
  autoFetch?: boolean;
}

export const ClinicalEvidenceReviewView: React.FC<ClinicalEvidenceReviewViewProps> = ({
  patientId,
  domain = 'diabetes',
  autoFetch = true,
}) => {
  const [evidence, setEvidence] = useState<EvidenceRetrievalResponse | null>(null);
  const [sources, setSources] = useState<EvidenceSourceRegistryEntry[] | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<EvidenceDomainCategory | 'all'>('all');
  const [showSourcesRegistry, setShowSourcesRegistry] = useState<boolean>(false);
  const [isLoadingSources, setIsLoadingSources] = useState<boolean>(false);

  const loadEvidence = useCallback(async () => {
    if (!patientId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res =
        domain === 'cardiovascular'
          ? await fetchPatientCardiovascularEvidence(patientId)
          : await fetchPatientDiabetesEvidence(patientId);
      setEvidence(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg || 'Failed to retrieve clinical guideline evidence references.');
    } finally {
      setIsLoading(false);
    }
  }, [patientId, domain]);

  useEffect(() => {
    if (autoFetch && patientId) {
      loadEvidence();
    }
  }, [autoFetch, patientId, loadEvidence]);

  const toggleSourcesRegistry = async () => {
    if (!showSourcesRegistry && !sources) {
      setIsLoadingSources(true);
      try {
        const sourceList = await fetchEvidenceSources();
        setSources(sourceList);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setError(`Failed to retrieve evidence source registry: ${msg}`);
      } finally {
        setIsLoadingSources(false);
      }
    }
    setShowSourcesRegistry((prev) => !prev);
  };

  const getSourceBadge = (organization: string, sourceId: string) => {
    const orgUpper = organization.toUpperCase();
    const idUpper = sourceId.toUpperCase();

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
  };

  const formatDomainLabel = (category: EvidenceDomainCategory) => {
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
        return 'Cardiovascular Risk Prevention';
      default:
        return String(category).replace(/_/g, ' ');
    }
  };

  const availableCategories = useMemo(() => {
    if (!evidence?.references) return [];
    const set = new Set<EvidenceDomainCategory>();
    for (const ref of evidence.references) {
      set.add(ref.domain_category);
    }
    return Array.from(set);
  }, [evidence]);

  const filteredReferences = useMemo(() => {
    if (!evidence?.references) return [];
    if (selectedCategory === 'all') return evidence.references;
    return evidence.references.filter((ref) => ref.domain_category === selectedCategory);
  }, [evidence, selectedCategory]);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-teal-700" />
            <h3 className="text-sm font-semibold text-slate-900 tracking-tight">
              {domain === 'cardiovascular'
                ? 'Supporting Evidence & Clinical Guidelines • Cardiovascular (ASCVD)'
                : 'Supporting Evidence & Clinical Guidelines • Step 5'}
            </h3>
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200">
              Verified Guidelines
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Authoritative clinical consensus recommendations grounded in verified practice guidelines
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleSourcesRegistry}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors cursor-pointer"
          >
            <Layers className="w-3.5 h-3.5 text-slate-500" />
            <span>{showSourcesRegistry ? 'Hide Registry' : 'Registered Sources'}</span>
          </button>

          <button
            onClick={loadEvidence}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-teal-800 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>{isLoading ? 'Retrieving...' : 'Refresh Evidence'}</span>
          </button>
        </div>
      </div>

      {/* Authoritative Sources Registry Drawer (Collapsible) */}
      {showSourcesRegistry && (
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-900">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-700" />
              <span>Registered Authoritative Evidence Sources</span>
            </div>
            <span className="text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600">
              {sources ? `${sources.length} Registries Active` : 'Verifying...'}
            </span>
          </div>

          {isLoadingSources && (
            <p className="text-xs text-slate-500">Loading verified evidence source registry...</p>
          )}

          {sources && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              {sources.map((src) => {
                const badge = getSourceBadge(src.organization, src.source_id);
                return (
                  <div key={src.source_id} className="p-3 rounded-lg bg-white border border-slate-200 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${badge.className}`}>
                        {badge.label}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        {src.edition_year} Edition
                      </span>
                    </div>
                    <div className="font-semibold text-slate-800 text-[11px] leading-snug">
                      {src.title}
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono">
                      {src.source_id}
                    </div>
                    <p className="text-[10px] text-slate-600 italic line-clamp-2">
                      {src.citation_metadata}
                    </p>
                    <a
                      href={src.official_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[10px] font-medium text-teal-700 hover:text-teal-900 pt-1"
                    >
                      <span>Official Registry Page</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-900 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading && !evidence && (
        <div className="py-8 text-center text-xs text-slate-500 space-y-2">
          <div className="inline-block w-5 h-5 border-2 border-teal-600 border-t-transparent rounded-full animate-spin" />
          <p className="font-medium text-slate-700">Retrieving verified clinical practice guidelines...</p>
          <p className="text-[11px] text-slate-400">
            {domain === 'cardiovascular'
              ? 'Mapping patient cardiovascular risk factors to consensus recommendations without generative hallucinations'
              : 'Mapping patient clinical trajectory to consensus recommendations without generative hallucinations'}
          </p>
        </div>
      )}

      {/* Evidence Content Body */}
      {evidence && (
        <div className="space-y-5">
          {/* Informational Decision Support Disclaimer Banner */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-slate-800">
              <Info className="w-3.5 h-3.5 text-teal-700" />
              <span>Guideline Evidence for Clinician Informational Context Only</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              {evidence.disclaimer}
            </p>
            <p className="text-[10px] text-slate-500 italic">
              Practice guidelines inform clinical judgment. The system does not emit drug dosages, convert citations into automated treatment orders, or replace individualized clinician care.
            </p>
          </div>

          {/* Traceability Metadata Bar & Domain Category Filters */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium text-slate-700">Filter Guideline Domain:</span>
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  onClick={() => setSelectedCategory('all')}
                  className={`px-2 py-0.5 text-[11px] rounded-md transition-colors cursor-pointer ${
                    selectedCategory === 'all'
                      ? 'bg-teal-700 text-white font-medium'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  All ({evidence.references.length})
                </button>
                {availableCategories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-2 py-0.5 text-[11px] rounded-md transition-colors cursor-pointer ${
                      selectedCategory === cat
                        ? 'bg-teal-700 text-white font-medium'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {formatDomainLabel(cat)}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono self-start sm:self-center">
              <span>{evidence.total_references} Verified References</span>
              <span>•</span>
              <span>Provider: {evidence.provider_id}</span>
            </div>
          </div>

          {/* Empty State */}
          {filteredReferences.length === 0 && (
            <div className="p-6 rounded-xl border border-dashed border-slate-200 bg-slate-50/50 text-center text-xs text-slate-500 space-y-1">
              <BookOpen className="w-5 h-5 text-slate-400 mx-auto" />
              <p className="font-medium text-slate-700">No Matched Guideline References</p>
              <p className="text-[11px] text-slate-400 max-w-md mx-auto">
                No verified guideline references match the selected domain category. No synthetic references or ungrounded claims are emitted.
              </p>
            </div>
          )}

          {/* Evidence Cards Grid */}
          <div className="space-y-3.5">
            {filteredReferences.map((ref) => {
              const badge = getSourceBadge(ref.organization, ref.source_id);
              return (
                <div
                  key={ref.evidence_id}
                  className="p-4 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-all text-xs space-y-2.5 shadow-2xs"
                >
                  {/* Card Header: Organization, Status, Edition, Domain Tag */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${badge.className}`}>
                        {badge.label}
                      </span>
                      <span className="font-semibold text-slate-900 text-xs">
                        {ref.guideline_title}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        <span>Verified Status</span>
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                        {ref.publication_version}
                      </span>
                    </div>
                  </div>

                  {/* Section / Chapter (if documented) & Domain Tag */}
                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                    <span className="text-teal-800 bg-teal-50 px-2 py-0.5 rounded font-medium border border-teal-100">
                      {formatDomainLabel(ref.domain_category)}
                    </span>
                    {ref.section_chapter && (
                      <span className="text-slate-600 bg-slate-100 px-2 py-0.5 rounded font-mono text-[10px] border border-slate-200">
                        {ref.section_chapter}
                      </span>
                    )}
                    {ref.recommendation_identifier && (
                      <span className="text-indigo-800 bg-indigo-50 px-2 py-0.5 rounded font-mono text-[10px] border border-indigo-200">
                        Rec {ref.recommendation_identifier}
                      </span>
                    )}
                  </div>

                  {/* Relevance Rationale / Scope Description */}
                  <div className="text-[11px] text-slate-700 leading-relaxed bg-slate-50/70 p-2.5 rounded-lg border border-slate-150">
                    <span className="font-semibold text-slate-800 block mb-0.5">
                      Clinical Scope & Relevance Rationale:
                    </span>
                    <p className="text-slate-600">{ref.scope_description}</p>
                  </div>

                  {/* Verifiable Bibliographic Citation */}
                  <div className="text-[10px] font-mono text-slate-500 bg-slate-50 px-2.5 py-1.5 rounded border border-slate-200/80 leading-relaxed">
                    <span className="font-bold text-slate-700 not-italic">Citation: </span>
                    <span>{ref.citation_text}</span>
                  </div>

                  {/* Official Publication Link Action */}
                  <div className="flex items-center justify-between pt-1 border-t border-slate-100">
                    <span className="text-[10px] font-mono text-slate-400">
                      ID: {ref.evidence_id}
                    </span>

                    <a
                      href={ref.official_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-teal-800 hover:text-teal-900 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-lg transition-colors cursor-pointer"
                    >
                      <span>View Official Publication</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Traceability Footer */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[10px] text-slate-400 pt-2 border-t border-slate-100 font-mono">
            <span>
              Evidence Retrieval Domain: <strong>{evidence.domain}</strong>
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-300" />
              Retrieved: {new Date(evidence.retrieved_at).toUTCString()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
