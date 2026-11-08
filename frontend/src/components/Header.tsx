import React from 'react';
import { Activity, ShieldAlert, Database, Calendar, Clock } from 'lucide-react';
import { Metadata } from '../types';

interface HeaderProps {
  metadata: Metadata | null;
  activeTab: 'overview' | 'map' | 'analytics' | 'anomalies' | 'quality';
  setActiveTab: (tab: 'overview' | 'map' | 'analytics' | 'anomalies' | 'quality') => void;
}

export const Header: React.FC<HeaderProps> = ({ metadata, activeTab, setActiveTab }) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Logo & Title */}
          <div className="flex items-center space-x-4">
            <div className="h-11 w-11 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 ring-1 ring-emerald-400/30">
              <Activity className="h-6 w-6 text-slate-950 font-bold" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold tracking-tight text-white">
                  India Civic Disruption Monitoring System
                </h1>
                <span className="px-2 py-0.5 text-xs font-semibold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
                  BBMP Bengaluru
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Empirical Civic Analytics & Historical Weekday Anomaly Surveillance
              </p>
            </div>
          </div>

          {/* Freshness & Metadata status badge */}
          {metadata && (
            <div className="hidden lg:flex items-center space-x-4 text-xs">
              <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-slate-400">Freshness:</span>
                <span className="font-semibold text-amber-300">{metadata.freshness_status}</span>
                <span className="text-slate-500">•</span>
                <span>{metadata.latest_record}</span>
              </div>

              <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300">
                <Database className="w-3.5 h-3.5 text-teal-400" />
                <span className="text-slate-400">Records:</span>
                <span className="font-semibold text-white">{metadata.total_records.toLocaleString()}</span>
              </div>
            </div>
          )}
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-1 border-t border-slate-800/60 py-2">
          {[
            { id: 'overview', label: 'Overview & Highlights' },
            { id: 'map', label: 'Civic Map (Wards)' },
            { id: 'analytics', label: 'Time-Series & Categories' },
            { id: 'anomalies', label: 'Anomaly Surveillance' },
            { id: 'quality', label: 'Data Quality & Ingestion Audit' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 text-xs font-medium rounded-lg transition-all ${
                activeTab === tab.id
                  ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
};
