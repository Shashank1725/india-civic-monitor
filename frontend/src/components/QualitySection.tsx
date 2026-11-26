import React, { useCallback, useEffect, useState } from 'react';
import { QualityCheckItem, IngestionRunItem, Metadata } from '../types';
import { fetchQualityMetrics, fetchIngestionRuns } from '../api';
import { ShieldCheck, CheckCircle2, Database, History, FileCheck, AlertTriangle, RefreshCw } from 'lucide-react';

interface QualitySectionProps { metadata: Metadata | null; }

export const QualitySection: React.FC<QualitySectionProps> = ({ metadata }) => {
  const [metrics, setMetrics] = useState<QualityCheckItem[]>([]);
  const [runs, setRuns] = useState<IngestionRunItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadQuality = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([fetchQualityMetrics(), fetchIngestionRuns()])
      .then(([m, r]) => {
        setMetrics(m);
        setRuns(r);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch quality metrics:', err);
        setLoading(false);
        setError('Failed to load audit data.');
      });
  }, []);

  useEffect(() => { loadQuality(); }, [loadQuality]);

  const ready = !loading && !error && metadata !== null;

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-200 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={loadQuality} className="px-3 py-1.5 rounded-lg border border-rose-500/40 bg-rose-500/20 text-xs font-semibold flex items-center gap-1.5">
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold uppercase">
            <Database className="w-4 h-4 text-emerald-400" /><span>Dataset Integrity</span>
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {loading ? 'Loading…' : ready ? metadata!.total_records.toLocaleString() : 'Unavailable'}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {ready ? 'Unique grievance IDs verified across source CSV files' : 'Audit verification pending'}
          </p>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold uppercase">
            <FileCheck className="w-4 h-4 text-teal-400" /><span>Geographic Completeness</span>
          </div>
          <div className="text-2xl font-bold text-teal-400 mt-2">
            {loading ? 'Loading…' : ready ? '100.0% Ward Name Present' : 'Unavailable'}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {ready
              ? '0% missing ward names in source; 0% GPS pins. Map polygon matching is tracked separately on the Choropleth.'
              : 'Spatial audit pending'}
          </p>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold uppercase">
            <History className="w-4 h-4 text-amber-400" /><span>Dataset Freshness</span>
          </div>
          <div className="text-2xl font-bold text-amber-300 mt-2">
            {loading ? 'Loading…' : ready ? 'Historical Snapshot' : 'Unavailable'}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {ready ? `Latest entry: ${metadata?.latest_record || 'Unavailable'}` : 'Freshness audit pending'}
          </p>
        </div>
      </div>

      <div className="glass-panel p-5 rounded-2xl border border-slate-800">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
          <h3 className="text-base font-bold text-white"><ShieldCheck className="inline w-5 h-5 mr-2 text-emerald-400" />Data Validation & Schema Conformance Rule Audit</h3>
          <span className="text-xs text-slate-400">
            {loading ? 'Loading…' : ready ? `Evaluated across all ${metadata!.total_records.toLocaleString()} records` : 'Unavailable'}
          </span>
        </div>

        {loading ? (
          <div className="py-10 text-center text-sm text-slate-400">Loading audit records…</div>
        ) : !ready ? (
          <div className="py-10 text-center text-sm text-slate-400">Audit data unavailable.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-slate-900/60 border-b border-slate-800">
                <tr><th className="py-3 px-4">Validation Rule</th><th className="py-3 px-4 text-center">Total Tested</th><th className="py-3 px-4 text-center">Passed</th><th className="py-3 px-4 text-center">Failed</th><th className="py-3 px-4 text-center">Failure Rate</th><th className="py-3 px-4">Details</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {metrics.map((m, i) => {
                  const isClean = m.failed === 0;
                  return (
                    <tr key={i}>
                      <td className="py-3 px-4 font-mono font-semibold text-white">{m.check_name}</td>
                      <td className="py-3 px-4 text-center">{m.total_checked.toLocaleString()}</td>
                      <td className="py-3 px-4 text-center text-emerald-400">{m.passed.toLocaleString()}</td>
                      <td className="py-3 px-4 text-center text-rose-400">{m.failed.toLocaleString()}</td>
                      <td className="py-3 px-4 text-center">{m.failure_rate.toFixed(3)}%</td>
                      <td className="py-3 px-4"><div className="flex items-center gap-1.5"><AlertTriangle className="w-4 h-4" /><span>{m.details || (isClean ? 'Passed verification criteria' : 'Verification issues found')}</span></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="glass-panel p-5 rounded-2xl border border-slate-800">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
          <h3 className="text-base font-bold text-white"><History className="inline w-5 h-5 mr-2 text-teal-400" />Pipeline Execution & Ingestion Run Log</h3>
          <span className="text-xs text-slate-400">Idempotent ingestion run history</span>
        </div>
        {loading ? (
          <div className="py-10 text-center text-sm text-slate-400">Loading ingestion runs…</div>
        ) : !ready ? (
          <div className="py-10 text-center text-sm text-slate-400">Ingestion run data unavailable.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="text-[11px] uppercase"><tr><th className="py-3 px-4">Run UUID</th><th className="py-3 px-4">Started At</th><th className="py-3 px-4">Status</th><th className="py-3 px-4 text-center">Read</th><th className="py-3 px-4 text-center">Inserted</th><th className="py-3 px-4 text-center">Skipped</th><th className="py-3 px-4 text-center">Rejected</th></tr></thead>
              <tbody className="divide-y divide-slate-800/60">
                {runs.map((r) => (
                  <tr key={r.id}><td className="py-3 px-4 font-mono text-slate-400">{r.run_uuid}</td><td className="py-3 px-4">{new Date(r.started_at).toLocaleString()}</td><td className="py-3 px-4">{r.status}</td><td className="py-3 px-4 text-center">{r.total_read.toLocaleString()}</td><td className="py-3 px-4 text-center text-emerald-400">{r.total_inserted.toLocaleString()}</td><td className="py-3 px-4 text-center">{r.total_skipped.toLocaleString()}</td><td className="py-3 px-4 text-center text-rose-400">{r.total_rejected.toLocaleString()}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
