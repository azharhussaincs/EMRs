import React from 'react';
import { Tag, BookOpen, Clock } from 'lucide-react';
import type { DiseaseDomainRegistryEntry } from '@/types/clinical';

interface DomainOverviewProps {
  domains: DiseaseDomainRegistryEntry[];
}

export const DomainOverview: React.FC<DomainOverviewProps> = ({ domains }) => {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
      <div className="mb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900 tracking-tight">
            Target Chronic Disease Domains
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Four high-burden disease trajectories evaluated by the clinical risk engine
          </p>
        </div>
        <span className="text-[11px] font-medium text-slate-600 bg-slate-100 px-2.5 py-1 rounded-md self-start sm:self-center border border-slate-200">
          4 Active Disease Profiles
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {domains.map((domain) => (
          <div
            key={domain.domain}
            className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-2 mb-2">
              <h3 className="text-xs font-semibold text-slate-900">
                {domain.display_name}
              </h3>
              <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-200/80 text-slate-700">
                {domain.domain.replace(/_/g, ' ')}
              </span>
            </div>

            <p className="text-xs text-slate-600 mb-3 leading-relaxed">
              {domain.description}
            </p>

            {/* Core Biomarkers */}
            <div className="pt-2 border-t border-slate-200/70 text-xs">
              <span className="text-[11px] font-semibold text-slate-700 block mb-1">
                Standard Biomarkers (LOINC):
              </span>
              <div className="flex flex-wrap gap-1.5">
                {domain.primary_biomarkers.map((b) => (
                  <span
                    key={b.name}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white border border-slate-200 text-[11px] text-slate-700"
                  >
                    <span>{b.name}</span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      ({b.unit})
                    </span>
                  </span>
                ))}
              </div>
            </div>

            {/* Evidence Guideline */}
            <div className="mt-3 pt-2 border-t border-slate-200/70 flex items-center justify-between text-[11px] text-slate-500">
              <span className="flex items-center gap-1 truncate">
                <BookOpen className="w-3 h-3 text-slate-400 shrink-0" />
                <span className="truncate">
                  {domain.consensus_guidelines[0]?.organization || 'Consensus Guidelines'}
                </span>
              </span>
              <span className="flex items-center gap-1 shrink-0 font-medium text-slate-600">
                <Clock className="w-3 h-3 text-slate-400" />
                {domain.target_risk_horizons.join(', ')}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
