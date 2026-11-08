import React from 'react';
import { Files, MapPin, AlertTriangle, CheckCircle2, Layers, ShieldCheck } from 'lucide-react';
import { Metadata, AreaSummary, AnomalyItem } from '../types';

interface OverviewCardsProps {
  metadata: Metadata | null;
  areas: AreaSummary[];
  anomalies: AnomalyItem[];
  filteredTotal: number;
}

export const OverviewCards: React.FC<OverviewCardsProps> = ({
  metadata,
  areas,
  anomalies,
  filteredTotal,
}) => {
  const anomalyCount = anomalies.filter((a) => a.is_anomaly).length;

  const cards = [
    {
      title: 'Total Grievances',
      value: metadata ? metadata.total_records.toLocaleString() : '---',
      subtitle: `${metadata?.days_span || 0} days recorded (2020–2025)`,
      icon: Files,
      color: 'from-blue-500/20 to-indigo-500/10',
      border: 'border-blue-500/30',
      iconColor: 'text-blue-400',
    },
    {
      title: 'Current Filter Volume',
      value: filteredTotal ? filteredTotal.toLocaleString() : '0',
      subtitle: 'Complaints in selected criteria',
      icon: Layers,
      color: 'from-emerald-500/20 to-teal-500/10',
      border: 'border-emerald-500/30',
      iconColor: 'text-emerald-400',
    },
    {
      title: 'BBMP Monitored Wards',
      value: metadata ? metadata.total_wards.toString() : '---',
      subtitle: '100% Ward name coverage',
      icon: MapPin,
      color: 'from-purple-500/20 to-violet-500/10',
      border: 'border-purple-500/30',
      iconColor: 'text-purple-400',
    },
    {
      title: 'Spike Anomalies Flagged',
      value: anomalyCount.toString(),
      subtitle: 'Statistically anomalous (Z ≥ 2.5σ)',
      icon: AlertTriangle,
      color: anomalyCount > 0 ? 'from-amber-500/20 to-orange-500/10' : 'from-slate-800 to-slate-850',
      border: anomalyCount > 0 ? 'border-amber-500/30' : 'border-slate-700/40',
      iconColor: anomalyCount > 0 ? 'text-amber-400' : 'text-slate-400',
    },
    {
      title: 'Spatial Completeness',
      value: '100% Ward Level',
      subtitle: 'Choropleth (0% Lat/Lon pins in source)',
      icon: CheckCircle2,
      color: 'from-cyan-500/20 to-blue-500/10',
      border: 'border-cyan-500/30',
      iconColor: 'text-cyan-400',
    },
    {
      title: 'Pipeline Ingestion Audit',
      value: '0 Duplicates',
      subtitle: 'Strict unique constraint & upsert',
      icon: ShieldCheck,
      color: 'from-teal-500/20 to-emerald-500/10',
      border: 'border-teal-500/30',
      iconColor: 'text-teal-400',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <div
            key={i}
            className={`p-4 rounded-xl border bg-gradient-to-br ${c.color} ${c.border} glass-panel glass-panel-hover flex flex-col justify-between`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                {c.title}
              </span>
              <Icon className={`w-5 h-5 ${c.iconColor}`} />
            </div>
            <div className="mt-3">
              <div className="text-2xl font-bold tracking-tight text-white">{c.value}</div>
              <div className="text-xs text-slate-400 mt-1 truncate">{c.subtitle}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
