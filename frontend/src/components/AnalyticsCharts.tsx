import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';
import { DailyAggregate, CategoryAggregate, AreaSummary } from '../types';
import { TrendingUp, PieChart as PieIcon, BarChart3 } from 'lucide-react';

interface AnalyticsChartsProps {
  dailyData: DailyAggregate[];
  categoryData: CategoryAggregate[];
  areas: AreaSummary[];
  onSelectWard: (ward: string) => void;
}

const CATEGORY_COLORS = [
  '#38bdf8', '#34d399', '#f59e0b', '#f43f5e', '#a855f7',
  '#06b6d4', '#10b981', '#fb923c', '#e879f9', '#64748b'
];

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({
  dailyData,
  categoryData,
  areas,
  onSelectWard,
}) => {
  // Top 10 wards
  const topWards = areas.slice(0, 10);
  const topCategories = categoryData.slice(0, 8);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 1. Complaints Over Time */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800 lg:col-span-2">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-bold text-white">
              Grievance Influx Trend Over Time
            </h3>
          </div>
          <span className="text-xs text-slate-400">
            {dailyData.length} active time points
          </span>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={dailyData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="complaintGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="#64748b"
                tick={{ fontSize: 11 }}
                minTickGap={40}
              />
              <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '8px',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
                labelStyle={{ color: '#facc15' }}
                itemStyle={{ color: '#facc15' }}
              />
              <Area
                type="monotone"
                dataKey="complaint_count"
                name="Total Complaints"
                stroke="#10b981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#complaintGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Top Complaint Categories */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <PieIcon className="w-5 h-5 text-teal-400" />
            <h3 className="text-base font-bold text-white">
              Top Complaint Categories
            </h3>
          </div>
          <span className="text-xs text-slate-400">By volume percentage</span>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={topCategories}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" stroke="#64748b" tick={{ fontSize: 10 }} />
              <YAxis
                dataKey="category"
                type="category"
                stroke="#94a3b8"
                tick={{ fontSize: 10 }}
                width={110}
              />
              <Tooltip
                labelStyle={{
                    color: '#facc15',
                    fontWeight: 'bold',
                }}
                formatter={(val: any, name: any, item: any) => [
                  `${Number(val).toLocaleString()} (${item.payload.percentage}%)`,
                  'Complaints',
                ]}
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '8px',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="complaint_count" radius={[0, 4, 4, 0]}>
                {topCategories.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 3. Top Reported Wards */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <BarChart3 className="w-5 h-5 text-sky-400" />
            <h3 className="text-base font-bold text-white">
              Top 10 Monitored Wards
            </h3>
          </div>
          <span className="text-xs text-slate-400">Click to filter</span>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={topWards}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 30, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" stroke="#64748b" tick={{ fontSize: 10 }} />
              <YAxis
                dataKey="ward_name"
                type="category"
                stroke="#94a3b8"
                tick={{ fontSize: 10 }}
                width={95}
              />
              <Tooltip
                formatter={(val: any) => [`${Number(val).toLocaleString()}`, 'Complaints']}
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '8px',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
              />
              <Bar
                dataKey="total_complaints"
                fill="#38bdf8"
                radius={[0, 4, 4, 0]}
                onClick={(item: any) => onSelectWard(item.ward_name)}
                cursor="pointer"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
