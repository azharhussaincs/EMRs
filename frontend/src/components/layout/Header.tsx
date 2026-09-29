import React from 'react';
import { Activity, ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react';

interface HeaderProps {
  isBackendConnected: boolean;
}

export const Header: React.FC<HeaderProps> = ({ isBackendConnected }) => {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Branding */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-teal-600 flex items-center justify-center text-white shadow-xs">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 tracking-tight text-base">
                Clinical Risk AI
              </span>
              <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                EMR Platform
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Generative AI-Based Multi-Disease Risk Stratification
            </p>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-200 bg-slate-50 text-xs">
            {isBackendConnected ? (
              <span className="flex items-center gap-1.5 text-emerald-700 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Backend Connected
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-amber-700 font-medium">
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                Backend Standby (:8000)
              </span>
            )}
          </div>

          <div className="hidden md:flex items-center gap-1 px-2.5 py-1.5 rounded-md border border-slate-200 text-slate-600 text-xs">
            <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
            <span>HIPAA §164.312 Active</span>
          </div>
        </div>
      </div>
    </header>
  );
};
