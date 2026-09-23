# BASELINE_VARIABLE_SET_v1

Non-negotiable starter pack for onboarding any company.

## Targets (per company)
- Total variables: **8–25**
- Weights sum: **0.85–1.15**
- At least **2 variables** with `is_zero_lag: true` (if applicable)
- At least **1 leading** variable (`lag_weeks < 0` OR a true external leading indicator)

## Required buckets

### 1) Company reported (MUST have 3–8)
Pick the company’s “core scoreboard”.
- Revenue / net fees / sales growth (or equivalent)
- Operating margin / EBITDA margin (one)
- Volume vs price OR units OR headcount OR utilisation (one+)
- Cash / conversion / working capital (if relevant)

### 2) Macro leading (MUST have 2–6)
Industry-specific demand indicators that move **before** the company reports.
Examples:
- Hiring demand, PMI/new orders, housing starts, travel volumes, ad spend indices,
  credit spreads, freight rates, etc.

### 3) Operating lever (MUST have 1)
One variable that directly reflects execution capacity.
Examples:
- Headcount, consultant productivity, utilisation, backlog, pricing, churn, pipeline.

### 4) FX (OPTIONAL 0–4, only if material)
If >20% revenue outside reporting currency, include:
- 1–3 key FX pairs OR a weighted FX basket estimate.

### 5) Commodity / input (OPTIONAL 0–4, only if relevant)
Only if raw materials/energy are material drivers.
Examples:
- Oil, gas, palm oil, electricity, paper, freight indices.

## Naming + conventions
- `feed_id`: snake_case, stable over time, no ticker prefix required
- `category`: one of:
  - fx, commodity, macro_leading, company_reported, subsidiary_leading,
    language_sentiment, capital_allocation, sector_data
- `threshold_*`: MUST include numeric comparator + time window:
  - Good: ">= 5.0% for 2 consecutive quarters"
  - Bad: "improving", "stable"

## Output expectations
- `v1.variables.json` MUST be schema-clean (no placeholders for required fields).
- Unknown ideas go in notes/backlog elsewhere (not in the canonical file).