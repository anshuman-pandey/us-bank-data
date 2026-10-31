# Reproducible bank cohorts

Available in `us-bank-data==0.2.0`, imported as `usbankdata`.

## One quarter with no source requests

```python
from usbankdata import snapshot

data = snapshot(quarter="2026Q2", edition="2026-q2-r1")
assert len(data.rows) == 4313
cohort = data.select(
    states=["NC"], bank_classes=["N", "SM", "NM", "SB", "SI", "SL"],
    min_assets_usd=100_000_000, max_assets_usd=3_000_000_000,
)
cohort.export("nc-banks.csv")
```

The bundle reproduces the public edition at
https://www.banksonsale.com/data/releases/2026-q2-r1 . Its report date is
June 30, 2026; original source retrievals are October 21, 2026. Original
financial JSON, manifest and five FDIC responses are retained. The loader
verifies pinned hashes, metrics and coverage before normalizing observations.

There are **4,313 institution financial records**, including 66 noninsured
institutions (NC) and 9 insured U.S. branches of foreign institutions (OI).
The source population has no current-active or bank-class filter. It is not
an insured-only list, a latest-data claim or a list of banks for sale. Only
2026Q2 edition `2026-q2-r1` is bundled. Other editions raise an error.

`select()` requires a single-quarter input. It records the anchor date,
parent dataset ID and filters. Asset bounds are integer dollars, minimum
inclusive and maximum exclusive. State/class filters are explicit code lists.
Empty selections are valid zero-row cohorts. CERTs absent from the snapshot
raise an error. There is no implicit active-bank filter.

## Aligned history for explicit banks

```python
from usbankdata import panel

data = panel(certs=[628, 3510, 58665], through="2026Q2", quarters=8)
data.export("bank-history.parquet")  # install us-bank-data[parquet]
```

Live requests require an explicit end quarter, one to 40 quarters, and one
to 100 distinct integer CERTs. Requests are grouped by quarter and sorted by
CERT, with bounded pagination, retries and timeouts. Population/index changes
within pagination, truncation, duplicate keys, omitted requested fields and
out-of-window records raise `DataError`. There is one `(cert, report_date)`
row per selected bank and quarter. An absent filing has
`report_available=False` and null metrics; a present filing can contain null
fields. Neither is filled from older reports. Inactive banks are retained.

Select banks by state or size on a quarter snapshot first, then pass its
CERTs to `panel()`, subject to the 100-bank bound. Retain that snapshot's
manifest alongside the history: a live explicit-CERT request records its
population but does not reconstruct why you chose it. `select()` rejects
multi-quarter input to prevent an ambiguous selection anchor.

`load_sample_cohort()` provides three offline interface samples, 24 rows across
2024Q3–2026Q2. They are not a matched or representative peer group. Their
retrieval dates differ from the quarter-wide edition; dataset IDs distinguish
the evidence. No automatic merge of those source vintages is performed.

## Units and identity

Fourteen metrics share the existing engine's audited definitions:

- `_usd`: U.S. dollars, converted once from source USD-thousands.
- `_pct`: percent; 12.5 means 12.5%. ROA and ROE are already annualized.
- CET1 is RBCT1CER; leverage is RBC1AAJ. They remain distinct.
- Null, reported zero, negative values and absent filings remain distinct.
- CERT identifies an institution, not a ticker, branch or consolidated parent.

Identity labels reflect source retrieval time, not a historical entity graph.
Live data can include revisions to past reports. Reporting date, filing date
when available, and retrieval date differ. These archives do not reconstruct
original-filing availability or uncollected historical vintages for backtests.

## Portable evidence

`BankCohort` exposes independent copies through `.rows`, `.banks`, `.to_dict()`
and `.manifest()`, with `.certs` for selected identifiers. Its schema is
`usbankdata.cohort.v1`, distinct from legacy BankPanel and website raw downloads.
Content-derived IDs cover normalized rows, definitions, population, selection,
dates, sources, coverage and edition information.

`validate()` checks content/source hashes, dates, unique keys, types, metric
definitions and coverage. `BankCohort.load("data.json")` verifies a saved JSON
envelope. Hashes detect changes, not underlying economic correctness, and are
not digital signatures.

- JSON includes observations and complete source evidence.
- CSV has a `.manifest.json` sidecar with the CSV hash and evidence.
- Parquet uses integer dollar/count columns when observations are integral and
  floating columns for percentages or fractional observations. Evidence is in
  schema metadata key `usbankdata`; a fractional value is never truncated.
- pandas stores evidence in `frame.attrs["usbankdata"]`.
- Polars returns a typed frame; retain `.manifest()` or a source-linked export.

Generic dataframe rewrites can discard metadata. Keep the original manifest
when creating a derived analysis. Empty exports retain their column schema.
No telemetry, account or paid service is required.

## Attribution and compatibility

Code is MIT. Original compilation and metadata are CC BY 4.0. Credit
**US Bank Data; BanksOnSale compilation and metadata, sourced from FDIC BankFind
Suite**, with the edition, report date and dataset ID. No FDIC endorsement is
implied. See `packages/us-bank-data/DATA_LICENSE.md`.

Legacy `bank()`, `search()`, `load_sample()`, `BankPanel` and `FDICClient` imports
remain compatible. New cohort features live in `usbankdata`. The public
`banksonsale-data==0.1.0` engine and its single-bank `banksonsale` metadata keys
are unchanged, preserving existing exports and identity hashes.
