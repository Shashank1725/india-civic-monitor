import React, { useEffect, useState, useCallback } from 'react';
import { Header } from './components/Header';
import { OverviewCards } from './components/OverviewCards';
import { FilterBar } from './components/FilterBar';
import { CivicMap } from './components/CivicMap';
import { AnalyticsCharts } from './components/AnalyticsCharts';
import { AnomalyTable } from './components/AnomalyTable';
import { AreaDrawer } from './components/AreaDrawer';
import { QualitySection } from './components/QualitySection';
import { FindingsSection } from './components/FindingsSection';
import { Footer } from './components/Footer';
import { RefreshCw, AlertCircle, Database, Loader2 } from 'lucide-react';

import {
  Metadata,
  FilterOptions,
  AreaSummary,
  DailyAggregate,
  CategoryAggregate,
  AnomalyItem,
  HealthStatus,
} from './types';
import {
  fetchHealth,
  fetchMetadata,
  fetchFilterOptions,
  fetchAreas,
  fetchDailyAggregates,
  fetchCategoryAggregates,
  fetchAnomalies,
} from './api';

export function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'map' | 'analytics' | 'anomalies' | 'quality'>('overview');

  // Metadata, Options & Health
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [dataReady, setDataReady] = useState<boolean>(false);

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
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  // Initial load & health monitoring
  const loadInitData = useCallback(async () => {
    setErrorMessage(null);
    try {
      const [h, meta, opts] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchMetadata(),
        fetchFilterOptions(),
      ]);

      if (h) setHealthStatus(h);
      setMetadata(meta);
      setFilterOptions(opts);

      if (opts.max_date) {
        setEndDate(opts.max_date);
        const d = new Date(opts.max_date);
        d.setDate(d.getDate() - 60);
        setStartDate(d.toISOString().split('T')[0]);
      }
    } catch (err: any) {
      console.error('Error fetching init config:', err);
      setErrorMessage(
        'Unable to reach backend service or database is still mounting. If the server just woke up, please wait a moment.'
      );
    }
  }, []);

  useEffect(() => {
    loadInitData();
  }, [loadInitData, refreshTrigger]);

  // Polling: If database is still empty or bootstrap is running, check /health every 5 seconds
  useEffect(() => {
    if (metadata && metadata.total_records > 0) return;

    const timer = setInterval(async () => {
      try {
        const h = await fetchHealth();
        setHealthStatus(h);
        if (h.data_ready || h.bootstrap_state === 'ready') {
          // Database is ready! Reload all metadata and dashboard data
          await loadInitData();
        }
      } catch (e) {
        // Server might be spinning up
      }
    }, 5000);

    return () => clearInterval(timer);
  }, [metadata, loadInitData]);

  // Fetch filtered data
  useEffect(() => {
    if (!metadata || metadata.total_records === 0) {
      setLoading(true);
      setDataReady(false);
      return;
    }

    setLoading(true);
    setDataReady(false);
    setErrorMessage(null);

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
        setDataReady(true);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error loading dashboard data:', err);
        setDataReady(false);
        setLoading(false);
        setErrorMessage('Failed to load records. Please retry.');
      });
  }, [startDate, endDate, selectedCategory, selectedWard, anomalyOnly, metadata]);

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

  const handleManualRetry = () => {
    setLoading(true);
    setErrorMessage(null);
    setRefreshTrigger((prev) => prev + 1);
  };

  const filteredTotal = dailyData.reduce((acc, curr) => acc + curr.complaint_count, 0);
  const isDbLoading = !metadata || metadata.total_records === 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header metadata={metadata} activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Status / Loading Notification Banner */}
        {isDbLoading && (
          <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-lg">
            <div className="flex items-center space-x-3">
              <Loader2 className="w-5 h-5 text-amber-400 animate-spin shrink-0" />
              <div>
                <div className="font-semibold text-sm text-amber-300">
                  Loading records…
                </div>
                <div className="text-xs text-amber-300/80 mt-0.5">
                  Render Free Tier boots from cold storage in ~1–2 minutes. Auto-refreshing in background...
                  {healthStatus?.bootstrap_detail ? ` (${healthStatus.bootstrap_detail})` : ''}
                </div>
              </div>
            </div>
            <button
              onClick={handleManualRetry}
              className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-xs font-semibold text-amber-200 flex items-center space-x-1.5 transition-all self-end sm:self-auto shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Error Alert Banner */}
        {errorMessage && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-lg">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
              <div>
                <div className="font-semibold text-sm text-rose-300">Data Loading Issue</div>
                <div className="text-xs text-rose-300/80 mt-0.5">{errorMessage}</div>
              </div>
            </div>
            <button
              onClick={handleManualRetry}
              className="px-3.5 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-xs font-semibold text-rose-200 flex items-center space-x-1.5 transition-all self-end sm:self-auto shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Connection</span>
            </button>
          </div>
        )}

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
          loading={loading || isDbLoading}
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
            {/* Key Findings Section */}
            <FindingsSection loading={loading || isDbLoading} dataReady={dataReady} />

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
              loading={loading || isDbLoading}
              error={errorMessage}
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
          <div className="space-y-6">
            <FindingsSection loading={loading || isDbLoading} dataReady={dataReady} />
            <AnalyticsCharts
              dailyData={dailyData}
              categoryData={categoryData}
              areas={areas}
              onSelectWard={(ward) => setDrawerWard(ward)}
            />
          </div>
        )}

        {/* Tab 4: Anomaly Surveillance Feed */}
        {activeTab === 'anomalies' && (
          <AnomalyTable
            anomalies={anomalies}
            onSelectWard={(ward) => setDrawerWard(ward)}
            loading={loading || isDbLoading}
            error={errorMessage}
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
