export interface HealthStatus {
  status: string;
  database: string;
  timestamp: string;
  data_ready: boolean;
  bootstrap_state: string;
  bootstrap_detail?: string;
}

export interface Metadata {
  total_records: number;
  total_wards: number;
  total_categories: number;
  earliest_record: string | null;
  latest_record: string | null;
  days_span: number;
  freshness_status: string;
  last_ingestion_time: string | null;
}

export interface FilterOptions {
  categories: string[];
  wards: string[];
  statuses: string[];
  min_date: string | null;
  max_date: string | null;
}

export interface AreaSummary {
  ward_name: string;
  total_complaints: number;
  open_complaints: number;
  closed_complaints: number;
  top_category?: string;
  latest_activity_date?: string;
}

export interface AreaDetail {
  ward_name: string;
  total_complaints: number;
  open_complaints: number;
  closed_complaints: number;
  category_breakdown: { category: string; count: number }[];
  recent_trend: { date: string; count: number; open_count: number; closed_count: number }[];
}

export interface DailyAggregate {
  date: string;
  complaint_count: number;
  open_count: number;
  closed_count: number;
}

export interface CategoryAggregate {
  category: string;
  complaint_count: number;
  percentage: number;
}

export interface AnomalyItem {
  date: string;
  ward_name: string;
  category: string;
  current_count: number;
  baseline_mean: number;
  baseline_std: number;
  sample_size: number;
  z_score: number;
  severity: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'NORMAL' | 'INSUFFICIENT_DATA';
  is_anomaly: boolean;
  explanation: string;
}

export interface QualityCheckItem {
  check_name: string;
  total_checked: number;
  passed: number;
  failed: number;
  failure_rate: number;
  details?: string;
}

export interface IngestionRunItem {
  id: number;
  run_uuid: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  total_read: number;
  total_inserted: number;
  total_skipped: number;
  total_rejected: number;
}
