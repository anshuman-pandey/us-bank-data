# US Bank Data changelog

## 0.2.0 — 2026-10-31

Adds an offline `snapshot()` of 4,313 FDIC institution financial records for
2026Q2, including the original manifest and five source-response pages. The
population includes NC/OI classes and is not an insured-only or active-only list.
Pinned hashes, normalized metric values and field coverage are verified at load.

Adds `BankCohort`, explicit single-quarter selection, live `panel()` queries for
up to 100 banks across 40 quarters, and `load_sample_cohort()`. Shared dates,
absent filings, missing values, zero/negative observations, population boundaries
and dollar/percent units remain explicit. CSV, JSON, pandas, typed Polars and
Parquet exports retain portable source evidence. Three new offline teaching
lessons cover screening, aligned history, and Polars/DuckDB agreement.

Existing single-bank APIs and the separately published `banksonsale-data==0.1.0`
engine are unchanged. No historical identity graph, original-filing vintages,
full Call Report coverage, new service account or background telemetry is added.

## 0.1.1 — 2026-10-29

Adds the descriptive public package `us-bank-data` and Python import `usbankdata`.
The repository is now `us-bank-data`; its existing releases and old GitHub URLs
remain accessible. The entry package delegates to the unchanged `banksonsale-data`
engine. Existing imports, archived sources, metric definitions and dataset IDs
are preserved.

## 0.1.0 — 2026-10-29

Initial public release: keyless FDIC institution lookup and explicit-quarter
financial panels; 14 reported fields with normalized USD and percent units;
archived raw-source evidence and integrity checks; JSON/CSV exports and optional
pandas, Polars and Parquet output; three real eight-quarter samples pinned through
2026Q2; two runnable research notebooks; and an optional independent OpenBB V5
router extension. No background telemetry or BanksOnSale account requirement.
