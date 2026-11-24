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
import { RefreshCw, AlertCircle, Loader2 } from 'lucide-react';
import { Metadata, FilterOptions, AreaSummary, DailyAggregate, CategoryAggregate, AnomalyItem, HealthStatus } from './types';
import { fetchHealth, fetchMetadata, fetchFilterOptions, fetchAreas, fetchDailyAggregates, fetchCategoryAggregates, fetchAnomalies } from './api';

export function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'map' | 'analytics' | 'anomalies' | 'quality'>('overview');
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [dataReady, setDataReady] = useState(false);
  const [startDate, setStartDate] = useState('2025-05-01');
  const [endDate, setEndDate] = useState('2025-06-19');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedWard, setSelectedWard] = useState('');
  const [anomalyOnly, setAnomalyOnly] = useState(false);
  const [drawerWard, setDrawerWard] = useState<string | null>(null);
  const [areas, setAreas] = useState<AreaSummary[]>([]);
  const [dailyData, setDailyData] = useState<DailyAggregate[]>([]);
  const [categoryData, setCategoryData] = useState<CategoryAggregate[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const loadInitData = useCallback(async () => {
    setErrorMessage(null);
    try {
      const [h, meta, opts] = await Promise.all([
        fetchHealth().catch(() => null), fetchMetadata(), fetchFilterOptions(),
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
    } catch (err) {
      console.error('Error fetching init config:', err);
      setDataReady(false);
      setErrorMessage('Unable to reach backend service or database is still mounting. Please retry when the service is ready.');
    }
  }, []);

  useEffect(() => { loadInitData(); }, [loadInitData, refreshTrigger]);

  useEffect(() => {
    if (metadata && metadata.total_records > 0) return;
    const timer = setInterval(async () => {
      try {
        const h = await fetchHealth();
        setHealthStatus(h);
        if (h.data_ready || h.bootstrap_state === 'ready') await loadInitData();
      } catch { /* Server may still be starting. */ }
    }, 5000);
    return () => clearInterval(timer);
  }, [metadata, loadInitData]);

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
      fetchAreas({ startDate: startDate || undefined, endDate: endDate || undefined, category: selectedCategory || undefined }),
      fetchDailyAggregates({ startDate: startDate || undefined, endDate: endDate || undefined, wardName: selectedWard || undefined, category: selectedCategory || undefined }),
      fetchCategoryAggregates({ startDate: startDate || undefined, endDate: endDate || undefined, wardName: selectedWard || undefined }),
      fetchAnomalies({ targetDate: endDate || undefined, category: selectedCategory || undefined, wardName: selectedWard || undefined, anomalyOnly }),
    ]).then(([a, d, c, anom]) => {
      setAreas(a);
      setDailyData(d);
      setCategoryData(c);
      setAnomalies(anom);
      setDataReady(true);
      setLoading(false);
    }).catch((err) => {
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
    setDataReady(false);
    setErrorMessage(null);
    setRefreshTrigger((prev) => prev + 1);
  };

  const filteredTotal = dailyData.reduce((acc, curr) => acc + curr.complaint_count, 0);
  const isDbLoading = !metadata || metadata.total_records === 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header metadata={metadata} activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {isDbLoading && (
          <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-200 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3"><Loader2 className="w-5 h-5 animate-spin" /><div><div className="font-semibold text-sm">Loading records…</div><div className="text-xs">Waiting for the database to become available.</div></div></div>
            <button onClick={handleManualRetry} className="px-3 py-1.5 rounded-lg border border-amber-500/40 bg-amber-500/20 text-xs font-semibold flex items-center gap-1.5"><RefreshCw className="w-3.5 h-3.5" />Retry</button>
          </div>
        )}

        {errorMessage && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-200 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3"><AlertCircle className="w-5 h-5" /><div><div className="font-semibold text-sm">Data Loading Issue</div><div className="text-xs">{errorMessage}</div></div></div>
            <button onClick={handleManualRetry} className="px-3.5 py-1.5 rounded-lg border border-rose-500/40 bg-rose-500/20 text-xs font-semibold flex items-center gap-1.5"><RefreshCw className="w-3.5 h-3.5" />Retry Connection</button>
          </div>
        )}

        <FilterBar options={filterOptions} startDate={startDate} setStartDate={setStartDate} endDate={endDate} setEndDate={setEndDate} selectedCategory={selectedCategory} setSelectedCategory={setSelectedCategory} selectedWard={selectedWard} setSelectedWard={setSelectedWard} anomalyOnly={anomalyOnly} setAnomalyOnly={setAnomalyOnly} onReset={handleResetFilters} />

        <OverviewCards metadata={metadata} areas={areas} anomalies={anomalies} filteredTotal={filteredTotal} loading={loading || isDbLoading} dataReady={dataReady} />

        {loading && <div className="w-full bg-slate-800 h-1 overflow-hidden rounded-full"><div className="bg-emerald-500 h-full w-1/3 animate-pulse" /></div>}

        {activeTab === 'overview' && (
          <div className="space-y-6">
            <FindingsSection loading={loading || isDbLoading} dataReady={dataReady} />
            <CivicMap areas={areas} anomalies={anomalies} selectedWard={drawerWard} onSelectWard={setDrawerWard} />
            <AnalyticsCharts dailyData={dailyData} categoryData={categoryData} areas={areas} onSelectWard={setDrawerWard} />
            <AnomalyTable anomalies={anomalies} onSelectWard={setDrawerWard} loading={loading || isDbLoading} error={errorMessage} />
          </div>
        )}

        {activeTab === 'map' && (
          <div className="space-y-6">
            <CivicMap areas={areas} anomalies={anomalies} selectedWard={drawerWard} onSelectWard={setDrawerWard} />
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="space-y-6">
            <FindingsSection loading={loading || isDbLoading} dataReady={dataReady} />
            <AnalyticsCharts dailyData={dailyData} categoryData={categoryData} areas={areas} onSelectWard={setDrawerWard} />
          </div>
        )}

        {activeTab === 'anomalies' && <AnomalyTable anomalies={anomalies} onSelectWard={setDrawerWard} loading={loading || isDbLoading} error={errorMessage} />}
        {activeTab === 'quality' && <QualitySection metadata={metadata} />}
      </main>

      <AreaDrawer wardName={drawerWard} onClose={() => setDrawerWard(null)} anomalies={anomalies} />
      <Footer />
    </div>
  );
}
export default App;
