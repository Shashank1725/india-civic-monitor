# Anomaly Validation and Missing-Date Policy

## Baseline

For each target date, ward, and category, the detector uses the preceding 8 observations that fall on the same weekday (for example, the previous 8 Mondays). The target date and future dates are excluded.

At least 4 historical observations are required. If fewer than 4 observations are available, the result is marked `INSUFFICIENT_DATA` and is not treated as an anomaly.

## Missing dates

The `daily_aggregates` table is a rollup and may not contain a row for every ward/category/date combination. Missing historical ward/category/date observations are excluded from the baseline sample rather than invented or filled with zero. This preserves the meaning of the 8-week window as observed comparable weekdays.

If the target ward/category/date is absent, the current count is 0. If the target date exists but a ward/category combination is absent, that combination is not evaluated as a target observation.

## Why use 2.5σ?

A 2.5σ threshold is a practical compromise:

- It is more conservative than 1.8σ and reduces weekday/count noise.
- It is less extreme than a 4σ-only rule, while the engine still classifies stronger spikes as high or critical.
- A separate minimum increase of at least 3 complaints prevents low-volume series from producing spikes on trivial count changes.
- The standard deviation has a 0.5 floor to avoid division-by-zero or near-zero variance inflation.

## Worked example

For the documented API example, 2025-06-16 was a Monday. Bapuji Nagar's Electrical category had 24 complaints. The historical Monday baseline was 0.8 complaints with standard deviation 0.7 and N=8.

\[
Z = \frac{24 - 0.8}{\max(0.7, 0.5)} \approx 32.88
\]

This exceeded the 2.5σ threshold and the 3-complaint practical increase threshold, so it was flagged as critical.

The example was validated by checking the target date and the eight preceding Monday observations in the rollup data. The target date was excluded from the baseline. The result is useful as an interpretable screening signal, but it does not prove the cause: a backlog-batching event, portal campaign, or external incident could produce the same spike.
