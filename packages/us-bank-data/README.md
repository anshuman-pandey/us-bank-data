# US Bank Data for Python

**Free, source-linked U.S. bank data: FDIC financials with explicit reporting
quarters, units and archived evidence.**

The public package name is `us-bank-data`; the Python import is `usbankdata`.
It provides one straightforward entry point for notebooks, classes, research
and applications. No account or API key is needed.

```python
from usbankdata import load_sample

panel = load_sample(58665)
print(panel.rows[-1])
panel.export("live-oak.csv")
```

Three real offline samples contain eight quarters each through 2026Q2. For a
live FDIC request with an explicit reporting window:

```python
from usbankdata import bank

panel = bank(58665).financials(quarters=8, through="2026Q2")
```

Fourteen selected fields cover assets, deposits, loans, equity, capital ratios,
ROA/ROE, offices and employees. Monetary `_usd` columns are U.S. dollars; `_pct`
columns are percentages. Missing observations stay missing. CERT identifies the
institution, not a listed holding company. This is selected institution-level
financial data, not a claim to provide all bank data or customer transactions.

CSV and JSON work without extra analysis libraries; pandas, Polars and Parquet
are optional. Source responses, definitions and dataset identities travel with
the export.

This small entry package installs the existing `banksonsale-data` engine and
reuses its implementation. Existing `import banksonsale_data` code continues
to work. Financial calculations, source snapshots and dataset identifiers are
unchanged. See the [repository](https://github.com/anshuman-pandey/us-bank-data)
for installation, notebooks, the field dictionary and the data contract.

Maintained by BanksOnSale. Original source: FDIC BankFind Suite. Code is MIT;
the engine's original sample compilation and metadata are CC BY 4.0 with
separate FDIC source attribution. No FDIC endorsement is implied.
