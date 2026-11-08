"""
analytics/anomalies.py
======================
Historical Weekday Anomaly Detection for BBMP Civic Grievances.

Methodology:
1. Aggregate complaints by day, ward, and category.
2. For any given (target_date, ward, category), identify historical comparable
   weekdays (e.g. past 8 to 12 Mondays before target_date).
3. Exclude target_date itself and all future records from baseline.
4. Calculate baseline statistics:
     - historical sample size (N)
     - baseline mean (μ)
     - baseline standard deviation (σ)
5. Calculate statistical Z-score with zero-variance protection:
     Z = (count - μ) / max(σ, 0.5)
6. Require both statistical significance (Z >= threshold) AND practical
   significance (count - μ >= min_abs_increase) to eliminate small-count noise.
7. Return rich anomaly metadata with plain-English explanation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, List, Optional, Dict

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
    severity: str        # "CRITICAL", "HIGH", "MODERATE", "NORMAL", "INSUFFICIENT_DATA"
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
    """
    Computes (mean, std, sample_size) for historical days sharing the same
    weekday as target_date, strictly before target_date.

    Args:
        counts_by_date: mapping from date -> count
        target_date: the date being evaluated (excluded from baseline)
        lookback_weeks: number of preceding weeks to check
        min_observations: minimum historical matching weekdays required
    """
    target_weekday = target_date.weekday()
    historical_counts: List[int] = []

    for w in range(1, lookback_weeks + 1):
        prev_date = target_date - timedelta(weeks=w)
        # Note: missing days in daily_aggregates mean 0 complaints occurred
        val = counts_by_date.get(prev_date, 0)
        historical_counts.append(val)

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
    """
    Evaluates whether current_count is anomalous compared to (mean, std).
    """
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

    # Protect against zero division or near-zero variance
    effective_std = max(std, 0.5)
    diff = current_count - mean
    z = diff / effective_std

    # Practical significance check: must have enough absolute increase
    is_anomaly = (z >= z_threshold) and (diff >= min_abs_increase)

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
            f"in {ward_name}, compared to a historical {day_name} baseline of {mean:.1f} (std: {std:.1f}, N={sample_size}). "
            f"Anomaly score: +{z:.2f}σ."
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
    """
    Database-backed anomaly detector querying the precomputed daily_aggregates table.
    """

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
        """
        Scans all wards and categories on target_date and flags anomalies.
        """
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

        # Build high-speed lookup mapping (ward, cat, date) -> count
        counts_lookup: Dict[tuple[str, str, date], int] = {}
        for row in df.itertuples(index=False):
            counts_lookup[(row.ward_name, row.category, row.agg_date)] = int(row.complaint_count)

        target_weekday = target_date.weekday()
        historical_dates = [target_date - timedelta(weeks=w) for w in range(1, lookback_weeks + 1)]

        results: List[AnomalyResult] = []
        target_df = df[df["agg_date"] == target_date]

        for row in target_df.itertuples(index=False):
            ward = row.ward_name
            cat = row.category
            current_cnt = int(row.complaint_count)

            # O(1) baseline computation across historical weekdays
            hist_counts = [counts_lookup.get((ward, cat, d), 0) for d in historical_dates]
            n = len(hist_counts)
            
            if n < 4:
                mean, std = 0.0, 0.0
            else:
                mean = sum(hist_counts) / n
                variance = sum((x - mean) ** 2 for x in hist_counts) / (n - 1) if n > 1 else 0.0
                std = variance ** 0.5

            res = evaluate_observation(
                target_date=target_date,
                ward_name=ward,
                category=cat,
                current_count=current_cnt,
                mean=mean,
                std=std,
                sample_size=n,
                z_threshold=z_threshold,
                min_abs_increase=min_abs_increase,
            )
            results.append(res)

        return results

    def get_top_anomalous_areas(
        self,
        start_date: date,
        end_date: date,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Returns wards with the highest frequency of anomalous spikes in the date range.
        """
        cur_date = start_date
        anomaly_counts: Dict[str, int] = {}
        
        while cur_date <= end_date:
            anomalies = self.get_anomalies_for_date(cur_date)
            for a in anomalies:
                if a.is_anomaly:
                    anomaly_counts[a.ward_name] = anomaly_counts.get(a.ward_name, 0) + 1
            cur_date += timedelta(days=1)

        sorted_wards = sorted(anomaly_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"ward_name": w, "anomaly_flags_count": c} for w, c in sorted_wards]
