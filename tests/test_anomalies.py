"""
tests/test_anomalies.py
======================
Unit tests for the historical weekday anomaly detection logic.
"""

from datetime import date, timedelta
import pytest

from analytics.anomalies import (
    compute_weekday_baseline,
    evaluate_observation,
)


def test_weekday_baseline_calculation():
    # Target date: Monday 2025-06-16
    target_date = date(2025, 6, 16)
    
    # 8 preceding Mondays with exact counts [10, 12, 11, 9, 10, 11, 10, 11]
    counts_map = {}
    history = [10, 12, 11, 9, 10, 11, 10, 11]
    for i, cnt in enumerate(history, 1):
        prev_monday = target_date - timedelta(weeks=i)
        counts_map[prev_monday] = cnt
        
    mean, std, n = compute_weekday_baseline(counts_map, target_date, lookback_weeks=8)
    assert n == 8
    assert round(mean, 2) == 10.5
    assert round(std, 2) > 0.8


def test_anomaly_detection_flags_spike():
    target_date = date(2025, 6, 16)
    # Mean is 10.0, std is 1.0, current count is 25 (spike of +15)
    res = evaluate_observation(
        target_date=target_date,
        ward_name="Horamavu",
        category="Electrical",
        current_count=25,
        mean=10.0,
        std=1.0,
        sample_size=8,
        z_threshold=2.5,
        min_abs_increase=3,
    )
    assert res.is_anomaly is True
    assert res.z_score >= 10.0
    assert res.severity in ["HIGH", "CRITICAL"]
    assert "Unusual spike on Monday" in res.explanation
    assert "Horamavu" in res.explanation


def test_normal_count_not_flagged():
    target_date = date(2025, 6, 16)
    res = evaluate_observation(
        target_date=target_date,
        ward_name="Horamavu",
        category="Electrical",
        current_count=11,
        mean=10.0,
        std=2.0,
        sample_size=8,
    )
    assert res.is_anomaly is False
    assert res.severity == "NORMAL"


def test_small_sample_size_handling():
    target_date = date(2025, 6, 16)
    # Only 2 observations available (< 4 required)
    res = evaluate_observation(
        target_date=target_date,
        ward_name="Horamavu",
        category="Forest",
        current_count=10,
        mean=1.0,
        std=0.5,
        sample_size=2,
        min_observations=4,
    )
    assert res.is_anomaly is False
    assert res.severity == "INSUFFICIENT_DATA"
    assert "Insufficient history" in res.explanation


def test_zero_variance_handled_gracefully():
    # If all previous 8 Mondays had exactly 0 complaints, std=0
    target_date = date(2025, 6, 16)
    res = evaluate_observation(
        target_date=target_date,
        ward_name="Horamavu",
        category="Water Crisis",
        current_count=1,  # Only 1 complaint — below min_abs_increase of 3
        mean=0.0,
        std=0.0,
        sample_size=8,
        min_abs_increase=3,
    )
    # Shouldn't raise ZeroDivisionError, and shouldn't falsely flag 1 complaint
    assert res.is_anomaly is False
