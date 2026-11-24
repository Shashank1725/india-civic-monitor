"""
analytics/anomalies.py
======================
Historical weekday anomaly detection for BBMP civic grievances.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import text

from database.database import engine

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    agg_date: date
    ward_name: str
    category: str
    current_count: int
    baseline_mean: float
    baseline_std: float
    sample_size: int
    z_score: float
    severity: str
    is_anomaly: bool
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.agg_date.isoformat() if hasattr(self.agg_date, "isoformat") else str(self.agg_date),
            "ward_name": self.ward_name,
            "category": self.category,
            "current_count": self.current_count,
            "baseline_mean": round(self.baseline_mean, 2),
            "baseline_std": round(self.baseline_std, 2),
            "sample_size": self.sample_size,
            "z_score": round(self.z_score, 2),
            "severity": self.severity,
            "is_anomaly": self.is_anomaly,
            "explanation": self.explanation,
        }


def compute_weekday_baseline(
    counts_by_date: Dict[date, int],
    target_date: date,
    lookback_weeks: int = 8,
    min_observations: int = 4,
) -> tuple[float, float, int]:
    """Compute a same-weekday baseline, excluding missing observations."""
    historical_counts: List[int] = []

    for w in range(1, lookback_weeks + 1):
        prev_date = target_date - timedelta(weeks=w)
        if prev_date in counts_by_date:
            historical_counts.append(counts_by_date[prev_date])

    n = len(historical_counts)
    if n < min_observations:
        return 0.0, 0.0, n

    s = pd.Series(historical_counts, dtype=float)
    mean = float(s.mean())
    std = float(s.std(ddof=1)) if n > 1 else 0.0
    return mean, std, n


def evaluate_observation(
    target_date: date,
    ward_name: str,
    category: str,
    current_count: int,
    mean: float,
    std: float,
    sample_size: int,
    z_threshold: float = 2.5,
    min_abs_increase: int = 3,
    min_observations: int = 4,
) -> AnomalyResult:
    day_name = target_date.strftime("%A")

    if sample_size < min_observations:
        return AnomalyResult(
            agg_date=target_date,
            ward_name=ward_name,
            category=category,
            current_count=current_count,
            baseline_mean=mean,
            baseline_std=std,
            sample_size=sample_size,
            z_score=0.0,
            severity="INSUFFICIENT_DATA",
            is_anomaly=False,
            explanation=f"Insufficient history ({sample_size} observations) to establish baseline for {ward_name}.",
        )

    effective_std = max(std, 0.5)
    diff = current_count - mean
    z = diff / effective_std
    is_anomaly = z >= z_threshold and diff >= min_abs_increase

    if z >= 4.0 and diff >= 8:
        severity = "CRITICAL"
    elif z >= 2.5 and diff >= 4:
        severity = "HIGH"
    elif z >= 1.8 and diff >= 2:
        severity = "MODERATE"
    else:
        severity = "NORMAL"

    if is_anomaly:
        explanation = (
            f"Unusual spike on {day_name} ({target_date}): {current_count} {category} complaints reported "
            f"in {ward_name}, compared to a historical {day_name} baseline of {mean:.1f} "
            f"(std: {std:.1f}, N={sample_size}). Anomaly score: +{z:.2f}σ."
        )
    else:
        explanation = (
            f"Normal activity on {day_name} ({target_date}): {current_count} complaints vs baseline {mean:.1f}."
        )

    return AnomalyResult(
        agg_date=target_date,
        ward_name=ward_name,
        category=category,
        current_count=current_count,
        baseline_mean=mean,
        baseline_std=std,
        sample_size=sample_size,
        z_score=z,
        severity=severity,
        is_anomaly=is_anomaly,
        explanation=explanation,
    )


class AnomalyDetector:
    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def get_anomalies_for_date(
        self,
        target_date: date,
        lookback_weeks: int = 8,
        z_threshold: float = 2.5,
        min_abs_increase: int = 3,
        category_filter: Optional[str] = None,
        ward_filter: Optional[str] = None,
    ) -> List[AnomalyResult]:
        """Scan target observations against same-weekday historical observations."""
        start_date = target_date - timedelta(weeks=lookback_weeks)
        query = """
            SELECT agg_date, ward_name, category, complaint_count
            FROM daily_aggregates
            WHERE agg_date >= :start_date AND agg_date <= :target_date
        """
        params: Dict[str, Any] = {
            "start_date": start_date.isoformat(),
            "target_date": target_date.isoformat(),
        }

        if category_filter:
            query += " AND category = :category"
            params["category"] = category_filter
        if ward_filter:
            query += " AND ward_name = :ward_name"
            params["ward_name"] = ward_filter

        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params=params)

        if df.empty:
            return []

        df["agg_date"] = pd.to_datetime(df["agg_date"]).dt.date

        counts_lookup: Dict[tuple[str, str, date], int] = {}
        for row in df.itertuples(index=False):
            counts_lookup[(row.ward_name, row.category, row.agg_date)] = int(row.complaint_count)

        historical_dates = [target_date - timedelta(weeks=w) for w in range(1, lookback_weeks + 1)]
        results: List[AnomalyResult] = []
        target_df = df[df["agg_date"] == target_date]

        for row in target_df.itertuples(index=False):
            ward = row.ward_name
            category = row.category
            current_count = int(row.complaint_count)

            # Missing rollup rows are absent observations, not zero-filled baseline observations.
            hist_counts = [
                counts_lookup[(ward, category, d)]
                for d in historical_dates
                if (ward, category, d) in counts_lookup
            ]
            n = len(hist_counts)

            if n < 4:
                mean, std = 0.0, 0.0
            else:
                mean = sum(hist_counts) / n
                variance = sum((x - mean) ** 2 for x in hist_counts) / (n - 1) if n > 1 else 0.0
                std = variance ** 0.5

            results.append(evaluate_observation(
                target_date=target_date,
                ward_name=ward,
                category=category,
                current_count=current_count,
                mean=mean,
                std=std,
                sample_size=n,
                z_threshold=z_threshold,
                min_abs_increase=min_abs_increase,
            ))

        return results

    def get_top_anomalous_areas(self, start_date: date, end_date: date, limit: int = 10):
        anomaly_counts: Dict[str, int] = {}
        cur_date = start_date

        while cur_date <= end_date:
            anomalies = self.get_anomalies_for_date(cur_date)
            for anomaly in anomalies:
                if anomaly.is_anomaly:
                    anomaly_counts[anomaly.ward_name] = anomaly_counts.get(anomaly.ward_name, 0) + 1
            cur_date += timedelta(days=1)

        sorted_wards = sorted(anomaly_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"ward_name": ward, "anomaly_flags_count": count} for ward, count in sorted_wards]
