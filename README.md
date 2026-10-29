# US Bank Data for Python

**Free U.S. bank data for Python: FDIC financials with the quarter, units and original source attached.**

[BanksOnSale.com](https://www.banksonsale.com) · [Public data catalog](https://www.banksonsale.com/data) · [Metric definitions](https://github.com/anshuman-pandey/us-bank-data/blob/v0.1.1/docs/METRICS.md) · [OpenBB extension](https://github.com/anshuman-pandey/us-bank-data/tree/v0.1.1/integrations/openbb)

Get a bank's quarterly financial panel, inspect the source evidence, and export
CSV, JSON or Parquet. The public `us-bank-data` package installs the existing standard-library
`banksonsale-data` engine: **no account, API key, paid subscription or background
telemetry**. `import usbankdata` and existing `import banksonsale_data` code use
the same implementation; the financial data contract and source evidence are unchanged.

Start offline with real, pinned samples. Use the same interface for a live FDIC
request when you want to choose another institution or reporting window.

## Install v0.1.1

Python 3.10 or newer. Install the versioned release wheel without requiring Git:

```bash
python -m pip install https://github.com/anshuman-pandey/us-bank-data/releases/download/v0.1.1/us_bank_data-0.1.1-py3-none-any.whl
```

Or install the tagged source with Git:

```bash
python -m pip install "us-bank-data @ git+https://github.com/anshuman-pandey/us-bank-data.git@v0.1.1#subdirectory=packages/us-bank-data"
```

The renamed package is installable from this GitHub release. Its PyPI publication is a separate step.
Optional extras include `pandas`, `polars`, `parquet`, and `notebooks`.
For example, install `pandas` in the same environment to use `.to_pandas()`.

## Useful output in four lines

```python
from usbankdata import load_sample

panel = load_sample(58665)  # Live Oak Banking Company; eight quarters through 2026Q2
print(panel.rows[-1])
panel.export("live-oak.csv")  # also writes live-oak.manifest.json with sources and units
```

The offline sample covers **2024-09-30 through 2026-06-30**. It is a frozen
example, not a claim about the latest available filing. Three sample institutions
are included: CERT 628, 3510 and 58665. They demonstrate the interface across
bank sizes; they are not a matched peer group or a ranking.

## Choose a bank and an exact reporting window

```python
from usbankdata import bank, search

matches = search("Live Oak", state="NC")  # inspect matches and select a CERT
panel = bank(58665).financials(quarters=8, through="2026Q2")
print(panel.document["bank"]["name"], panel.document["coverage"])
print(panel.dataset_id)
```

Omitting `through` asks FDIC for that bank's latest available reporting date and
records that default in the manifest. Different banks can have different latest
dates. Select the same explicit quarter when comparing banks. Requests are
bounded and transient failures have capped retries.

## Use your existing analysis tools

```python
frame = panel.to_pandas()       # optional pandas; evidence retained in frame.attrs["banksonsale"]
records = panel.rows            # independent copy of standard Python records
panel.export("live-oak.json")  # self-contained snapshot with archived evidence
panel.export("live-oak.parquet")  # optional pyarrow; evidence in schema metadata
```

CSV works in spreadsheets and DuckDB. `.to_polars()` is available with Polars
installed. See [the data contract](https://github.com/anshuman-pandey/us-bank-data/blob/v0.1.1/docs/DATA_CONTRACT.md) for nulls, units and
snapshot integrity. JSON from `panel.export()` is a BankPanel envelope; the
website's quarter-wide JSON download is a separate documented format.

## Run a real example

- [Bank financials and exports](https://github.com/anshuman-pandey/us-bank-data/blob/v0.1.1/notebooks/01_bank_financials.ipynb) — [Open in Colab](https://colab.research.google.com/github/anshuman-pandey/banksonsale-data/blob/v0.1.1/notebooks/01_bank_financials.ipynb).
- [Same-quarter comparison and SQL](https://github.com/anshuman-pandey/us-bank-data/blob/v0.1.1/notebooks/02_compare_banks.ipynb) — [Open in Colab](https://colab.research.google.com/github/anshuman-pandey/banksonsale-data/blob/v0.1.1/notebooks/02_compare_banks.ipynb).
- [Ready-to-open comparison CSV](https://github.com/anshuman-pandey/us-bank-data/blob/v0.1.1/examples/comparison-2026-q2.csv), with the [source manifest](https://github.com/anshuman-pandey/us-bank-data/blob/v0.1.1/examples/comparison-2026-q2.manifest.json).

The notebooks run locally without a cloud account. Their install cell retrieves
the tagged public release. Colab has its own sign-in requirements and limits.

## What you get

Fourteen reported fields cover assets, total and domestic deposits, equity,
intangibles, net loans, estimated uninsured deposits, core deposits, CET1,
leverage, annualized ROA/ROE, domestic offices and employees.

- Monetary columns end in `_usd` and are **U.S. dollars**, normalized once from FDIC's USD-thousands values.
- Ratios end in `_pct`: **12.5 means 12.5%**. ROA and ROE are already annualized by the source.
- CET1 uses **RBCT1CER**. Leverage uses **RBC1AAJ**. They remain distinct.
- Missing observations stay `None`. Reported zero and negative observations remain unchanged.
- Missing quarters remain explicit rows with `report_available=False`; older reports are never substituted.
- FDIC CERT identifies an institution, not a listed holding company, ticker or individual branch.

This is a small, versioned release of selected FDIC fields. It does not cover all
bank data, customers' accounts, live transactions, full Call Reports, transaction
prices or verified sale listings. Names and institution metadata reflect the
upstream source at retrieval, not a reconstructed historical identity timeline.

## Command line

```bash
us-bank-data sample --cert 58665 --output live-oak.csv
us-bank-data search "Live Oak" --state NC
us-bank-data financials --cert 58665 --quarters 8 --through 2026Q2 --output live-oak.json
us-bank-data definitions
```

## Continue the research in BanksOnSale

[Open Live Oak's public financial summary](https://www.banksonsale.com/banks/58665)
or [explore the BanksOnSale research workspace](https://www.banksonsale.com/discover).
The hosted product adds saved screens, watchlists, research dossiers, monitoring,
models and exports; some features require a subscription. Its data edition is
displayed separately and can differ from this package's selected period.

These are optional links. The package keeps working without an account, sends
no usage telemetry, and does not create a subscription. See [continuing your
research](https://github.com/anshuman-pandey/us-bank-data/blob/v0.1.1/docs/CONTINUE_IN_BANKSONSALE.md).

## OpenBB

The optional [independently maintained OpenBB V5 extension](https://github.com/anshuman-pandey/us-bank-data/tree/v0.1.1/integrations/openbb)
adds `obb.banksonsale`. It reuses this package and its definitions. It is not
bundled with or endorsed by OpenBB. The core package does not require OpenBB.

## Source, license and citation

Original source: [FDIC BankFind Suite](https://api.fdic.gov/banks/docs/).
BanksOnSale is an independent compiler; no FDIC affiliation or endorsement is implied.

Original code: [MIT](https://github.com/anshuman-pandey/us-bank-data/blob/v0.1.1/LICENSE). Sample compilation and original metadata:
[CC BY 4.0, with separate source attribution](https://github.com/anshuman-pandey/us-bank-data/blob/v0.1.1/DATA_LICENSE.md).
Use [CITATION.cff](https://github.com/anshuman-pandey/us-bank-data/blob/v0.1.1/CITATION.cff) and record the bank CERT, report dates and dataset ID.
SHA-256 checks detect changes to a snapshot; they are not a government signature
or proof that a filing is economically correct.

## Contributing and verification

See [CONTRIBUTING.md](https://github.com/anshuman-pandey/us-bank-data/blob/v0.1.1/CONTRIBUTING.md). Offline checks:

```bash
python -m pip install -e . -e packages/us-bank-data
python -m unittest discover -s tests -v
```

Network refreshes are explicit maintainer actions, not part of the default tests.
[Report a package issue](https://github.com/anshuman-pandey/us-bank-data/issues)
or [a source-data correction](https://www.banksonsale.com/corrections).
