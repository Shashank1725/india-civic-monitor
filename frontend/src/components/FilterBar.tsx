import React from 'react';
import { Filter, Calendar, Tag, MapPin, Zap, RotateCcw } from 'lucide-react';
import { FilterOptions } from '../types';

interface FilterBarProps {
  options: FilterOptions | null;
  startDate: string;
  setStartDate: (val: string) => void;
  endDate: string;
  setEndDate: (val: string) => void;
  selectedCategory: string;
  setSelectedCategory: (val: string) => void;
  selectedWard: string;
  setSelectedWard: (val: string) => void;
  anomalyOnly: boolean;
  setAnomalyOnly: (val: boolean) => void;
  onReset: () => void;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  options,
  startDate,
  setStartDate,
  endDate,
  setEndDate,
  selectedCategory,
  setSelectedCategory,
  selectedWard,
  setSelectedWard,
  anomalyOnly,
  setAnomalyOnly,
  onReset,
}) => {
  return (
    <div className="glass-panel p-4 rounded-xl border border-slate-800 flex flex-wrap items-center gap-3">
      <div className="flex items-center space-x-2 text-slate-400 mr-2 text-xs font-semibold uppercase tracking-wider">
        <Filter className="w-4 h-4 text-emerald-400" />
        <span>Filters</span>
      </div>

      {/* Date Range Start */}
      <div className="flex items-center space-x-2 bg-slate-900/90 border border-slate-700/60 rounded-lg px-3 py-1.5 text-xs">
        <Calendar className="w-3.5 h-3.5 text-slate-400" />
        <span className="text-slate-400">From:</span>
        <input
          type="date"
          value={startDate}
          min={options?.min_date || '2020-01-01'}
          max={options?.max_date || '2025-06-19'}
          onChange={(e) => setStartDate(e.target.value)}
          className="bg-transparent text-white focus:outline-none cursor-pointer"
        />
      </div>

      {/* Date Range End */}
      <div className="flex items-center space-x-2 bg-slate-900/90 border border-slate-700/60 rounded-lg px-3 py-1.5 text-xs">
        <Calendar className="w-3.5 h-3.5 text-slate-400" />
        <span className="text-slate-400">To:</span>
        <input
          type="date"
          value={endDate}
          min={options?.min_date || '2020-01-01'}
          max={options?.max_date || '2025-06-19'}
          onChange={(e) => setEndDate(e.target.value)}
          className="bg-transparent text-white focus:outline-none cursor-pointer"
        />
      </div>

      {/* Category Dropdown */}
      <div className="flex items-center space-x-2 bg-slate-900/90 border border-slate-700/60 rounded-lg px-3 py-1.5 text-xs">
        <Tag className="w-3.5 h-3.5 text-slate-400" />
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="bg-transparent text-white focus:outline-none max-w-[180px] truncate cursor-pointer"
        >
          <option value="" className="bg-slate-900 text-white">All Categories</option>
          {options?.categories.map((c) => (
            <option key={c} value={c} className="bg-slate-900 text-white">
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* Ward Dropdown */}
      <div className="flex items-center space-x-2 bg-slate-900/90 border border-slate-700/60 rounded-lg px-3 py-1.5 text-xs">
        <MapPin className="w-3.5 h-3.5 text-slate-400" />
        <select
          value={selectedWard}
          onChange={(e) => setSelectedWard(e.target.value)}
          className="bg-transparent text-white focus:outline-none max-w-[180px] truncate cursor-pointer"
        >
          <option value="" className="bg-slate-900 text-white">All Wards (199)</option>
          {options?.wards.map((w) => (
            <option key={w} value={w} className="bg-slate-900 text-white">
              {w}
            </option>
          ))}
        </select>
      </div>

      {/* Anomaly Mode Toggle */}
      <button
        onClick={() => setAnomalyOnly(!anomalyOnly)}
        className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
          anomalyOnly
            ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm shadow-amber-500/10'
            : 'bg-slate-900/80 text-slate-400 border-slate-700/60 hover:text-slate-200'
        }`}
      >
        <Zap className={`w-3.5 h-3.5 ${anomalyOnly ? 'text-amber-400' : 'text-slate-400'}`} />
        <span>Anomaly Spikes Only</span>
      </button>

      {/* Reset */}
      <button
        onClick={onReset}
        title="Reset all filters"
        className="ml-auto flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors border border-transparent hover:border-slate-700"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        <span>Reset</span>
      </button>
    </div>
  );
};
