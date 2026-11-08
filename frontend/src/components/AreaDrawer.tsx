import React, { useEffect, useState } from 'react';
import { AreaDetail, AnomalyItem } from '../types';
import { fetchAreaDetail } from '../api';
import {
  X,
  MapPin,
  CheckCircle,
  Clock,
  AlertTriangle,
  Layers,
  TrendingUp,
  ShieldCheck,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  AreaChart,
  Area,
  CartesianGrid,
} from 'recharts';

interface AreaDrawerProps {
  wardName: string | null;
  onClose: () => void;
  anomalies: AnomalyItem[];
}

export const AreaDrawer: React.FC<AreaDrawerProps> = ({ wardName, onClose, anomalies }) => {
  const [detail, setDetail] = useState<AreaDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!wardName) {
      setDetail(null);
      return;
    }

    setLoading(true);
    fetchAreaDetail(wardName)
      .then((data) => {
        setDetail(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching area detail:', err);
        setLoading(false);
      });
  }, [wardName]);

  if (!wardName) return null;

  const wardAnomalies = anomalies.filter(
    (a) => a.ward_name.toLowerCase() === wardName.toLowerCase() && a.is_anomaly
  );

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-slate-900 border-l border-slate-800 shadow-2xl z-50 overflow-y-auto p-6 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <MapPin className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">{wardName}</h2>
            <p className="text-xs text-slate-400">Detailed Ward Civic Profile & Temporal Breakdown</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-slate-400">
          <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mr-2" />
          <span>Loading ward metrics...</span>
        </div>
      ) : detail ? (
        <div className="space-y-6 mt-6">
          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
              <span className="text-[11px] text-slate-400 font-semibold uppercase">Total Complaints</span>
              <div className="text-xl font-bold text-white mt-1">
                {detail.total_complaints.toLocaleString()}
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
              <span className="text-[11px] text-slate-400 font-semibold uppercase">Resolved</span>
              <div className="text-xl font-bold text-emerald-400 mt-1">
                {detail.closed_complaints.toLocaleString()}
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
              <span className="text-[11px] text-slate-400 font-semibold uppercase">Pending</span>
              <div className="text-xl font-bold text-amber-400 mt-1">
                {detail.open_complaints.toLocaleString()}
              </div>
            </div>
          </div>

          {/* Anomaly banner if present */}
          {wardAnomalies.length > 0 && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300">
              <div className="flex items-center space-x-2 font-bold text-sm text-rose-400 mb-1">
                <AlertTriangle className="w-4 h-4" />
                <span>Active Historical Weekday Anomalies</span>
              </div>
              <ul className="text-xs space-y-1 mt-2 text-rose-200">
                {wardAnomalies.map((a, i) => (
                  <li key={i} className="list-disc list-inside">
                    {a.explanation}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recent Trend Chart */}
          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/50">
            <div className="flex items-center space-x-2 mb-3">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Recent Daily Activity Trend
              </h4>
            </div>
            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={detail.recent_trend} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 9 }} minTickGap={30} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 9 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      fontSize: '11px',
                    }}
                  />
                  <Area type="monotone" dataKey="count" stroke="#10b981" fill="#10b981" fillOpacity={0.2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Category Breakdown */}
          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/50">
            <div className="flex items-center space-x-2 mb-3">
              <Layers className="w-4 h-4 text-teal-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Category Distribution
              </h4>
            </div>
            <div className="space-y-2">
              {detail.category_breakdown.slice(0, 6).map((cat, i) => {
                const pct = Math.round((cat.count / detail.total_complaints) * 100);
                return (
                  <div key={i} className="text-xs">
                    <div className="flex justify-between text-slate-300 mb-1">
                      <span>{cat.category}</span>
                      <span className="font-semibold text-white">
                        {cat.count.toLocaleString()} ({pct}%)
                      </span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Limitations note */}
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 space-y-1">
            <div className="flex items-center space-x-1.5 text-slate-300 font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Data Governance & Privacy Protection</span>
            </div>
            <p>
              Records are aggregated at municipal ward granularity. Citizen contact details, phone numbers,
              and individual BBMP staff names are withheld to protect personal privacy.
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
};
