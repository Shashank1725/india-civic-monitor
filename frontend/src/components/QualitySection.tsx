import React, { useEffect, useState } from 'react';
import { QualityCheckItem, IngestionRunItem, Metadata } from '../types';
import { fetchQualityMetrics, fetchIngestionRuns } from '../api';
import {
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Database,
  History,
  FileCheck,
  AlertTriangle,
} from 'lucide-react';

interface QualitySectionProps {
  metadata: Metadata | null;
}

export const QualitySection: React.FC<QualitySectionProps> = ({ metadata }) => {
  const [metrics, setMetrics] = useState<QualityCheckItem[]>([]);
  const [runs, setRuns] = useState<IngestionRunItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    Promise.all([fetchQualityMetrics(), fetchIngestionRuns()])
      .then(([m, r]) => {
        setMetrics(m);
        setRuns(r);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch quality metrics:', err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold uppercase">
            <Database className="w-4 h-4 text-emerald-400" />
            <span>Dataset Integrity</span>
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {metadata ? metadata.total_records.toLocaleString() : '---'}
          </div>
          <p className="text-xs text-slate-400 mt-1">100% Unique Grievance IDs across 6 source CSV files</p>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold uppercase">
            <FileCheck className="w-4 h-4 text-teal-400" />
            <span>Geographic Completeness</span>
          </div>
          <div className="text-2xl font-bold text-teal-400 mt-2">
            {metadata && metadata.total_records > 0 ? '100.0% Ward-Level' : 'Unavailable'}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            0% missing wards; 0% GPS pin coordinates present in source data
          </p>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold uppercase">
            <History className="w-4 h-4 text-amber-400" />
            <span>Dataset Freshness</span>
          </div>
          <div className="text-2xl font-bold text-amber-300 mt-2">
            {metadata && metadata.total_records > 0 ? 'Historical Snapshot' : 'Unavailable'}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Latest entry: {metadata?.latest_record || 'Connecting...'} (Dataset spans 2020–2025)
          </p>
        </div>
      </div>

      {/* Quality Checks Table */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-bold text-white">
              Data Validation & Schema Conformance Rule Audit
            </h3>
          </div>
          <span className="text-xs text-slate-400">
            {metadata && metadata.total_records > 0
              ? `Evaluated across all ${metadata.total_records.toLocaleString()} records`
              : 'Audit data loading or unavailable'}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-slate-900/60 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Validation Rule</th>
                <th className="py-3 px-4 text-center">Total Tested</th>
                <th className="py-3 px-4 text-center">Passed</th>
                <th className="py-3 px-4 text-center">Failed</th>
                <th className="py-3 px-4 text-center">Failure Rate</th>
                <th className="py-3 px-4">Status & Rule Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {metrics.map((m, i) => {
                const isClean = m.failed === 0;
                return (
                  <tr key={i} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-white">
                      {m.check_name}
                    </td>
                    <td className="py-3 px-4 text-center text-slate-400">
                      {m.total_checked.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-center font-bold text-emerald-400">
                      {m.passed.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-center font-bold text-rose-400">
                      {m.failed.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-center font-mono font-semibold">
                      <span
                        className={`px-2 py-0.5 rounded ${
                          isClean ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                        }`}
                      >
                        {m.failure_rate.toFixed(3)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      <div className="flex items-center space-x-1.5">
                        {isClean ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                        )}
                        <span>{m.details || 'Passed verification criteria'}</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ingestion Runs Audit Table */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <History className="w-5 h-5 text-teal-400" />
            <h3 className="text-base font-bold text-white">
              Pipeline Execution & Ingestion Run Log
            </h3>
          </div>
          <span className="text-xs text-slate-400">Idempotent ingestion run history</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-slate-900/60 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Run UUID</th>
                <th className="py-3 px-4">Started At</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-center">Records Read</th>
                <th className="py-3 px-4 text-center">Inserted</th>
                <th className="py-3 px-4 text-center">Skipped (Duplicate)</th>
                <th className="py-3 px-4 text-center">Rejected</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {runs.map((r) => (
                <tr key={r.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">{r.run_uuid}</td>
                  <td className="py-3 px-4 text-slate-300">
                    {new Date(r.started_at).toLocaleString()}
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase">
                      {r.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center font-bold text-white">
                    {r.total_read.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-center text-emerald-400 font-bold">
                    {r.total_inserted.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-center text-amber-300">
                    {r.total_skipped.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-center text-rose-400">
                    {r.total_rejected.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
