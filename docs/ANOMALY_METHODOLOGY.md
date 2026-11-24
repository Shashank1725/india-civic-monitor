# Anomaly Validation and Missing-Date Policy

## Baseline

For each target date, ward, and category, the detector uses preceding calendar weeks with the same weekday (for example, the previous 8 Mondays). The target date and future dates are excluded from the baseline.

At least 4 observed historical ward/category/weekday observations are required. If fewer than 4 observations are available, the result is marked `INSUFFICIENT_DATA` and is not treated as an anomaly.

## Missing dates

The `daily_aggregates` table is a rollup and may not contain a row for every ward/category/date combination. Missing historical ward/category/date rows are excluded from the baseline sample rather than being zero-filled.

A missing target ward/category/date row means that ward/category combination is not evaluated for that target date. This avoids interpreting an absent aggregate row as a complaint observation.

## Why use 2.5σ?

A 2.5σ threshold is a practical compromise:

- It is stricter than 1.8σ and reduces weekday/count noise.
- It is less extreme than a 4σ-only rule; stronger spikes are still classified as high or critical.
- A separate minimum increase of at least 3 complaints prevents low-volume series from producing spikes on trivial count changes.
- The standard deviation has a 0.5 floor to avoid division-by-zero or near-zero variance inflation.

## Worked example

For the documented API example, 2025-06-16 was a Monday. Bapuji Nagar's Electrical category had 24 complaints. The historical Monday baseline was 0.8 complaints with standard deviation 0.7 and N=8.

\[
Z = \frac{24 - 0.8}{\max(0.7, 0.5)} \approx 33.14
\]

The API may report a slightly different rounded Z-score because it uses the unrounded standard deviation and then rounds to two decimal places. In the existing API example, the score is +32.88σ; both calculations demonstrate a result far above the 2.5σ threshold and 3-complaint practical threshold.

This example was reviewed against the target date and eight preceding Monday observations in the rollup data. The target date was excluded from the baseline. It is useful as an interpretable screening result: it identifies a large, unusual jump worth investigation, but it does not prove a real infrastructure failure or establish causation.
