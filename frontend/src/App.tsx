import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { OverviewCards } from './components/OverviewCards';
import { FilterBar } from './components/FilterBar';
import { CivicMap } from './components/CivicMap';
import { AnalyticsCharts } from './components/AnalyticsCharts';
import { AnomalyTable } from './components/AnomalyTable';
import { AreaDrawer } from './components/AreaDrawer';
import { QualitySection } from './components/QualitySection';
import { Footer } from './components/Footer';

import {
  Metadata,
  FilterOptions,
  AreaSummary,
  DailyAggregate,
  CategoryAggregate,
  AnomalyItem,
} from './types';
import {
  fetchMetadata,
  fetchFilterOptions,
  fetchAreas,
  fetchDailyAggregates,
  fetchCategoryAggregates,
  fetchAnomalies,
} from './api';

export function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'map' | 'analytics' | 'anomalies' | 'quality'>('overview');

  // Metadata & Options
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);

  // Active Filter States
  const [startDate, setStartDate] = useState<string>('2025-05-01');
  const [endDate, setEndDate] = useState<string>('2025-06-19');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedWard, setSelectedWard] = useState<string>('');
  const [anomalyOnly, setAnomalyOnly] = useState<boolean>(false);

  // Interactive Area Drawer State
  const [drawerWard, setDrawerWard] = useState<string | null>(null);

  // Data States
  const [areas, setAreas] = useState<AreaSummary[]>([]);
  const [dailyData, setDailyData] = useState<DailyAggregate[]>([]);
  const [categoryData, setCategoryData] = useState<CategoryAggregate[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Initial load
  useEffect(() => {
    Promise.all([fetchMetadata(), fetchFilterOptions()])
      .then(([meta, opts]) => {
        setMetadata(meta);
        setFilterOptions(opts);
        if (opts.max_date) {
          setEndDate(opts.max_date);
          // Set start date to 60 days before max date for snappy initial view
          const d = new Date(opts.max_date);
          d.setDate(d.getDate() - 60);
          setStartDate(d.toISOString().split('T')[0]);
        }
      })
      .catch((err) => console.error('Error fetching init config:', err));
  }, []);

  // Fetch filtered data
  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchAreas({
        startDate: startDate || undefined,
        endDate: endDate || undefined,
        category: selectedCategory || undefined,
      }),
      fetchDailyAggregates({
        startDate: startDate || undefined,
        endDate: endDate || undefined,
        wardName: selectedWard || undefined,
        category: selectedCategory || undefined,
      }),
      fetchCategoryAggregates({
        startDate: startDate || undefined,
        endDate: endDate || undefined,
        wardName: selectedWard || undefined,
      }),
      fetchAnomalies({
        targetDate: endDate || undefined,
        category: selectedCategory || undefined,
        wardName: selectedWard || undefined,
        anomalyOnly: anomalyOnly,
      }),
    ])
      .then(([a, d, c, anom]) => {
        setAreas(a);
        setDailyData(d);
        setCategoryData(c);
        setAnomalies(anom);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error loading dashboard data:', err);
        setLoading(false);
      });
  }, [startDate, endDate, selectedCategory, selectedWard, anomalyOnly]);

  const handleResetFilters = () => {
    if (filterOptions?.max_date) {
      setEndDate(filterOptions.max_date);
      const d = new Date(filterOptions.max_date);
      d.setDate(d.getDate() - 60);
      setStartDate(d.toISOString().split('T')[0]);
    }
    setSelectedCategory('');
    setSelectedWard('');
    setAnomalyOnly(false);
  };

  const filteredTotal = dailyData.reduce((acc, curr) => acc + curr.complaint_count, 0);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header metadata={metadata} activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Global Filter Bar */}
        <FilterBar
          options={filterOptions}
          startDate={startDate}
          setStartDate={setStartDate}
          endDate={endDate}
          setEndDate={setEndDate}
          selectedCategory={selectedCategory}
          setSelectedCategory={setSelectedCategory}
          selectedWard={selectedWard}
          setSelectedWard={setSelectedWard}
          anomalyOnly={anomalyOnly}
          setAnomalyOnly={setAnomalyOnly}
          onReset={handleResetFilters}
        />

        {/* Top KPI Metrics Cards */}
        <OverviewCards
          metadata={metadata}
          areas={areas}
          anomalies={anomalies}
          filteredTotal={filteredTotal}
        />

        {/* Loading Indicator Bar */}
        {loading && (
          <div className="w-full bg-slate-800 h-1 overflow-hidden rounded-full">
            <div className="bg-emerald-500 h-full w-1/3 animate-pulse" />
          </div>
        )}

        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <CivicMap
              areas={areas}
              anomalies={anomalies}
              selectedWard={drawerWard}
              onSelectWard={(ward) => setDrawerWard(ward)}
            />
            <AnalyticsCharts
              dailyData={dailyData}
              categoryData={categoryData}
              areas={areas}
              onSelectWard={(ward) => setDrawerWard(ward)}
            />
            <AnomalyTable
              anomalies={anomalies}
              onSelectWard={(ward) => setDrawerWard(ward)}
            />
          </div>
        )}

        {/* Tab 2: Map Focus */}
        {activeTab === 'map' && (
          <div className="space-y-6">
            <CivicMap
              areas={areas}
              anomalies={anomalies}
              selectedWard={drawerWard}
              onSelectWard={(ward) => setDrawerWard(ward)}
            />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {areas.slice(0, 18).map((area) => (
                <div
                  key={area.ward_name}
                  onClick={() => setDrawerWard(area.ward_name)}
                  className="glass-panel p-3.5 rounded-xl border border-slate-800 hover:border-emerald-500/40 cursor-pointer transition-all flex items-center justify-between"
                >
                  <div>
                    <h4 className="font-semibold text-white text-xs">{area.ward_name}</h4>
                    <span className="text-[11px] text-slate-400">
                      {area.open_complaints} pending / {area.closed_complaints} resolved
                    </span>
                  </div>
                  <span className="font-bold text-emerald-400 text-sm">
                    {area.total_complaints.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 3: Detailed Analytics */}
        {activeTab === 'analytics' && (
          <AnalyticsCharts
            dailyData={dailyData}
            categoryData={categoryData}
            areas={areas}
            onSelectWard={(ward) => setDrawerWard(ward)}
          />
        )}

        {/* Tab 4: Anomaly Surveillance Feed */}
        {activeTab === 'anomalies' && (
          <AnomalyTable
            anomalies={anomalies}
            onSelectWard={(ward) => setDrawerWard(ward)}
          />
        )}

        {/* Tab 5: Data Quality & Ingestion Runs */}
        {activeTab === 'quality' && <QualitySection metadata={metadata} />}
      </main>

      {/* Interactive Ward Drilldown Drawer */}
      <AreaDrawer
        wardName={drawerWard}
        onClose={() => setDrawerWard(null)}
        anomalies={anomalies}
      />

      <Footer />
    </div>
  );
}
export default App;
