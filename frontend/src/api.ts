import {
  Metadata,
  FilterOptions,
  AreaSummary,
  AreaDetail,
  DailyAggregate,
  CategoryAggregate,
  AnomalyItem,
  QualityCheckItem,
  IngestionRunItem,
} from './types';

const API_BASE = '/api';

export async function fetchMetadata(): Promise<Metadata> {
  const res = await fetch(`${API_BASE}/metadata`);
  if (!res.ok) throw new Error('Failed to fetch metadata');
  return res.json();
}

export async function fetchFilterOptions(): Promise<FilterOptions> {
  const res = await fetch(`${API_BASE}/filters`);
  if (!res.ok) throw new Error('Failed to fetch filter options');
  return res.json();
}

export async function fetchAreas(params?: {
  startDate?: string;
  endDate?: string;
  category?: string;
}): Promise<AreaSummary[]> {
  const sp = new URLSearchParams();
  if (params?.startDate) sp.append('start_date', params.startDate);
  if (params?.endDate) sp.append('end_date', params.endDate);
  if (params?.category) sp.append('category', params.category);

  const res = await fetch(`${API_BASE}/areas?${sp.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch areas');
  return res.json();
}

export async function fetchAreaDetail(wardName: string): Promise<AreaDetail> {
  const res = await fetch(`${API_BASE}/areas/${encodeURIComponent(wardName)}`);
  if (!res.ok) throw new Error(`Failed to fetch area detail for ${wardName}`);
  return res.json();
}

export async function fetchDailyAggregates(params?: {
  startDate?: string;
  endDate?: string;
  wardName?: string;
  category?: string;
}): Promise<DailyAggregate[]> {
  const sp = new URLSearchParams();
  if (params?.startDate) sp.append('start_date', params.startDate);
  if (params?.endDate) sp.append('end_date', params.endDate);
  if (params?.wardName) sp.append('ward_name', params.wardName);
  if (params?.category) sp.append('category', params.category);

  const res = await fetch(`${API_BASE}/aggregates/daily?${sp.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch daily aggregates');
  return res.json();
}

export async function fetchCategoryAggregates(params?: {
  startDate?: string;
  endDate?: string;
  wardName?: string;
}): Promise<CategoryAggregate[]> {
  const sp = new URLSearchParams();
  if (params?.startDate) sp.append('start_date', params.startDate);
  if (params?.endDate) sp.append('end_date', params.endDate);
  if (params?.wardName) sp.append('ward_name', params.wardName);

  const res = await fetch(`${API_BASE}/aggregates/categories?${sp.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch category aggregates');
  return res.json();
}

export async function fetchAnomalies(params?: {
  targetDate?: string;
  category?: string;
  wardName?: string;
  anomalyOnly?: boolean;
}): Promise<AnomalyItem[]> {
  const sp = new URLSearchParams();
  if (params?.targetDate) sp.append('target_date', params.targetDate);
  if (params?.category) sp.append('category', params.category);
  if (params?.wardName) sp.append('ward_name', params.wardName);
  if (params?.anomalyOnly !== undefined) sp.append('anomaly_only', String(params.anomalyOnly));

  const res = await fetch(`${API_BASE}/anomalies?${sp.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch anomalies');
  return res.json();
}

export async function fetchQualityMetrics(): Promise<QualityCheckItem[]> {
  const res = await fetch(`${API_BASE}/data-quality`);
  if (!res.ok) throw new Error('Failed to fetch data quality metrics');
  return res.json();
}

export async function fetchIngestionRuns(): Promise<IngestionRunItem[]> {
  const res = await fetch(`${API_BASE}/ingestion-runs`);
  if (!res.ok) throw new Error('Failed to fetch ingestion runs');
  return res.json();
}
