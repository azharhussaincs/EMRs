import React from 'react';
import { AlertCircle } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="mt-auto border-t border-slate-200 bg-white py-4 px-6 text-xs text-slate-500">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <p className="text-[11px] leading-relaxed text-slate-600">
            <strong>Clinical Decision Support Boundary:</strong> Designed to assist licensed clinicians. Does not issue autonomous diagnoses or therapeutic orders.
          </p>
        </div>
        <div className="text-[11px] text-slate-400 shrink-0">
          Target Diseases: Diabetes • Cardiovascular • CKD • Cancer
        </div>
      </div>
    </footer>
  );
};
