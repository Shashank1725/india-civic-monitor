import React from 'react';
import { ShieldAlert, ExternalLink, Info, Heart } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-slate-800 bg-slate-950 mt-16 py-8 text-xs text-slate-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4">
        {/* Important Disclaimer Alert */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 text-slate-400 flex items-start space-x-3">
          <ShieldAlert className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-semibold text-slate-200">
              Civic Monitoring & Ethics Disclaimer
            </h4>
            <p className="text-[11px] leading-relaxed">
              This system is an empirical civic disruption monitoring tool built for exploratory civic research,
              municipal capacity planning, and academic data science. It is <strong>NOT</strong> an emergency navigation
              or real-time hazard system. Complaint volume reflects civic reporting activity and citizen engagement,
              not proof of area emergency.
            </p>
          </div>
        </div>

        <div className="flex flex-col md:flex-row items-center justify-between pt-4 border-t border-slate-900 text-[11px] gap-2">
          <div className="flex items-center space-x-4">
            <span>Bruhat Bengaluru Mahanagara Palike (BBMP) Grievances Data</span>
            <span>•</span>
            <span>Spatial Boundaries: DataMeet (CC BY 4.0)</span>
          </div>
          <div>
            <span>India Civic Disruption Monitoring System • Portfolio Project</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
