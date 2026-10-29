# US Bank Data changelog

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
