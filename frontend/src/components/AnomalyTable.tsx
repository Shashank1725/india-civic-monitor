import React from 'react';
import { AlertTriangle, ArrowUpRight, CheckCircle2 } from 'lucide-react';
import { AnomalyItem } from '../types';

interface AnomalyTableProps {
  anomalies: AnomalyItem[];
  onSelectWard: (ward: string) => void;
  loading?: boolean;
  error?: string | null;
}

export const AnomalyTable: React.FC<AnomalyTableProps> = ({ anomalies, onSelectWard, loading = false, error = null }) => {
  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">CRITICAL SPIKE</span>;
      case 'HIGH':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">HIGH SPIKE</span>;
      case 'MODERATE':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">MODERATE</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-800 text-slate-400 border border-slate-700">NORMAL</span>;
    }
  };

  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <h3 className="text-base font-bold text-white">Historical Weekday Anomaly Surveillance Feed</h3>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 font-semibold">
            {loading ? 'Loading…' : error ? 'Unavailable' : `${anomalies.length} Flagged Events`}
          </span>
        </div>
      </div>

      {loading ? (
        <div className="py-12 text-center text-slate-400 flex flex-col items-center justify-center space-y-2">
          <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Loading records… Evaluating historical weekday rolling baselines & Z-scores.</p>
        </div>
      ) : error ? (
        <div className="py-12 text-center text-slate-400">
          <p className="text-sm">Unavailable — anomaly data could not be loaded.</p>
        </div>
      ) : anomalies.length === 0 ? (
        <div className="py-12 text-center text-slate-500">
          <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-emerald-500/50" />
          <p className="text-sm">No abnormal disruption spikes detected for the current filter criteria.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-slate-900/60 border-b border-slate-800">
              <tr><th className="py-3 px-4">Date</th><th className="py-3 px-4">Ward / Area</th><th className="py-3 px-4">Category</th><th className="py-3 px-4 text-center">Observed</th><th className="py-3 px-4 text-center">Baseline (μ ± σ)</th><th className="py-3 px-4 text-center">Z-Score</th><th className="py-3 px-4">Severity</th><th className="py-3 px-4">Explanation</th><th className="py-3 px-4 text-right">Action</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {anomalies.map((a, i) => (
                <tr key={i} className="hover:bg-slate-800/40 cursor-pointer" onClick={() => onSelectWard(a.ward_name)}>
                  <td className="py-3 px-4 font-mono text-slate-400">{a.date}</td>
                  <td className="py-3 px-4 font-semibold text-white">{a.ward_name}</td>
                  <td className="py-3 px-4">{a.category}</td>
                  <td className="py-3 px-4 text-center font-bold text-white">{a.current_count}</td>
                  <td className="py-3 px-4 text-center text-slate-400">{a.baseline_mean.toFixed(1)} ± {a.baseline_std.toFixed(1)} (N={a.sample_size})</td>
                  <td className="py-3 px-4 text-center font-mono font-bold text-emerald-400">+{a.z_score.toFixed(1)}σ</td>
                  <td className="py-3 px-4">{getSeverityBadge(a.severity)}</td>
                  <td className="py-3 px-4 text-slate-400 max-w-sm">{a.explanation}</td>
                  <td className="py-3 px-4 text-right"><button onClick={(e) => { e.stopPropagation(); onSelectWard(a.ward_name); }} className="inline-flex items-center gap-1 text-emerald-400 text-xs font-semibold"><span>Drill down</span><ArrowUpRight className="w-3.5 h-3.5" /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
