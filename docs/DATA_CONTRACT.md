# BanksOnSale Data contract 1.0

`BankPanel` contains one explicitly selected FDIC institution and a contiguous
calendar-quarter window of 1–40 quarters. A report can be unavailable within the
window. Its row remains present with `report_available=false` and null metrics;
no prior or subsequent quarter is substituted.

## Identity and time

- `bank.cert`: FDIC CERT. This identifies an institution, not its listed parent, ticker or branch.
- `bank.rssd_id`: the source's RSSD ID, when reported.
- `bank.name`, city, state and activity metadata: institution attributes at retrieval. These are not a historical identity reconstruction. Consult `bank_class` when available; the API can cover different FDIC institution classes.
- `requested_dates` and `rows[].report_date`: exact financial reporting quarter ends.
- `sources[].retrieved_at`: UTC time this package fetched the response.
- `sources[].source_index_created_at`: FDIC index creation timestamp, not the report date.
- `report_date_defaulted`: true only when the caller omitted `through` and the client selected that bank's latest available report date.

## Numbers

Money is normalized from FDIC USD thousands to **USD** exactly once. Ratio
observations retain **percent** units: 12.5 is 12.5%, not 0.125%. ROA/ROE are
annualized by the source and never annualized again. The definition for each
column records its raw field, multiplier, reporting basis and documentation URL.
CET1 is RBCT1CER; leverage is RBC1AAJ. Equity/assets is a separate derived
accounting ratio and must not be relabeled as either regulatory ratio.

Blank/NA/absent observations become null. Reported zeros and negative values are
retained. Missing/inapplicable values are not inferred from nearby observations.
Malformed, boolean, infinite or nonnumeric financial values fail validation.
A reported zero's economic applicability is not inferred.

## Evidence and portability

Each panel carries the selected field definitions, coverage counts, exact FDIC
request URLs, retrieved raw JSON, source-response SHA-256 hashes, a content hash
and a branded dataset ID. Integrity checks detect byte/content changes; they are
not a digital signature from FDIC or independent verification of a filing.

`panel.export('file.json')` saves the self-contained envelope. Reload it with
`BankPanel.load('file.json')`. The website's all-institution quarter JSON is a
separate format; do not pass its raw array to `BankPanel.load()`.

CSV exports include a matching `.manifest.json` file carrying evidence, units,
coverage and a SHA-256 of the CSV bytes. Keep those files together. Parquet embeds
the manifest in schema metadata under `banksonsale`. pandas uses
`frame.attrs['banksonsale']`. Polars users should retain `panel.manifest()` or
export a self-contained artifact alongside the DataFrame.

## Scope

The current release exposes 14 selected FDIC financial fields. It does not
provide full Call Report/XBRL coverage, customer-level data, real-time balances,
complete ownership history, transaction valuations or verified sale intent.
Current upstream revisions are not information-as-known-at-the-time history.
This is research software, not an investment, regulatory or safety rating.
