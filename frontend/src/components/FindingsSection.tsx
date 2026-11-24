import React from 'react';
import {
  Lightbulb,
  Zap,
  MapPin,
  TrendingUp,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface FindingsSectionProps {
  loading: boolean;
  dataReady: boolean;
}

export const FindingsSection: React.FC<FindingsSectionProps> = ({ loading, dataReady }) => {
  const [expanded, setExpanded] = React.useState<boolean>(true);

  const findings = [
    {
      id: 'finding-1',
      title: 'Infrastructure Concentration: Electrical & Waste Dominate 65.9% of Complaints',
      dateRange: 'Jan 1, 2020 – Jun 19, 2025 (All 5.5 Years)',
      icon: Zap,
      accentColor: 'border-blue-500/30 text-blue-400 bg-blue-500/10',
      numbers: [
        { label: 'Electrical Complaints', value: '310,128', sub: '40.45% of total' },
        { label: 'Solid Waste (Garbage)', value: '195,153', sub: '25.46% of total' },
        { label: 'Road Maintenance', value: '111,535', sub: '14.55% of total' },
      ],
      insight:
        'Over 80.4% of municipal friction points in Bengaluru stem from just three core utility services. Streetlight failures, power fluctuations, and garbage collection delays drive the bulk of reporting activity.',
      limitations:
        'Reflects citizen portal adoption and reporting propensity via BBMP Sahaya. High digital-literacy wards may log more tickets than offline wards, overestimating relative service deficits.',
    },
    {
      id: 'finding-2',
      title: 'Geographic Asymmetry: Peripheral Growth Corridors Experience Highest Pressure',
      dateRange: 'Jan 1, 2020 – Jun 19, 2025 (All 199 Wards)',
      icon: MapPin,
      accentColor: 'border-purple-500/30 text-purple-400 bg-purple-500/10',
      numbers: [
        { label: 'Top 5 Wards Volume', value: '84,009', sub: '11.0% of all complaints' },
        { label: '#1 Ward (Jnanabharathi)', value: '18,323', sub: '2.39% share' },
        { label: '#2 Ward (Horamavu)', value: '17,437', sub: '2.27% share' },
      ],
      insight:
        'The top 5 grievance wards are Jnanabharathi, Horamavu, Rajarajeshwari Nagar, Begur, and Thanisandra, all in expanding peripheral growth corridors.',
      limitations:
        'The source contains ward names but no GPS coordinates. Sub-ward street clusters cannot be located from this dataset alone.',
    },
    {
      id: 'finding-3',
      title: 'Temporal Surge: 2024 Grievance Volume Surged by +73.7%',
      dateRange: 'Jan 2020 – Dec 2024 (Annual Trajectory)',
      icon: TrendingUp,
      accentColor: 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10',
      numbers: [
        { label: '2023 Volume', value: '119,140', sub: 'Baseline year' },
        { label: '2024 Volume', value: '207,016', sub: '+73.7% annual jump' },
        { label: '2025 Pace (5.5 mos)', value: '126,974', sub: 'Sustained high volume' },
      ],
      insight:
        'Grievance volume rose from 119,140 in 2023 to 207,016 in 2024. The increase may reflect both civic disruption and greater adoption of digital reporting channels.',
      limitations:
        'The dataset cannot separate changes in actual service conditions from changes in portal awareness or intake volume without external weather and reporting-access data.',
    },
  ];

  return (
    <div className="glass-panel rounded-2xl border border-slate-800 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Lightbulb className="w-5 h-5 text-amber-400" />
          <h2 className="text-base font-bold text-white">Key Empirical Findings & Real-World Insights</h2>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            {loading ? 'Loading…' : dataReady ? '766,648 Records (2020–2025)' : 'Unavailable'}
          </span>
        </div>
        {dataReady && !loading && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-slate-400 hover:text-white flex items-center space-x-1"
          >
            <span>{expanded ? 'Collapse' : 'Expand'}</span>
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}
      </div>

      {loading && (
        <div className="py-8 text-center text-sm text-slate-400">Loading findings…</div>
      )}

      {!loading && !dataReady && (
        <div className="py-8 text-center text-sm text-slate-400">Unavailable — findings could not be loaded.</div>
      )}

      {dataReady && !loading && expanded && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 pt-2">
          {findings.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.id}
                className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-start space-x-2">
                    <div className={`p-1.5 rounded-lg border ${f.accentColor}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-xs font-bold text-white leading-snug">{f.title}</h3>
                      <span className="text-[10px] text-slate-400 block mt-0.5">{f.dateRange}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 my-3 pt-2 border-t border-slate-800/80">
                    {f.numbers.map((n, i) => (
                      <div key={i} className="text-center p-1.5 rounded-lg bg-slate-950/60">
                        <div className="text-xs font-bold text-white">{n.value}</div>
                        <div className="text-[9px] text-slate-400 truncate mt-0.5">{n.sub}</div>
                      </div>
                    ))}
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">{f.insight}</p>
                </div>

                <div className="pt-2 border-t border-slate-800/60 text-[11px] text-slate-400 flex items-start space-x-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-400/80 shrink-0 mt-0.5" />
                  <span>
                    <strong className="text-slate-300">Methodological Limitation:</strong> {f.limitations}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
