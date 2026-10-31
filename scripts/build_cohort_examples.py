"""Generate the three offline cohort lessons and reproducible starter scripts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {
        "cell_type": "code",
        "metadata": {},
        "source": text.splitlines(keepends=True),
        "execution_count": None,
        "outputs": [],
    }


install = """import importlib.metadata
import importlib.util
import subprocess
import sys

try:
    installed = importlib.metadata.version("us-bank-data") == "0.2.0"
except importlib.metadata.PackageNotFoundError:
    installed = False
if not installed:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "us-bank-data==0.2.0"])
"""
teaching_install = (
    install
    + """
if any(importlib.util.find_spec(name) is None for name in ["polars", "duckdb", "pyarrow"]):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "us-bank-data[teaching]==0.2.0"])
"""
)

lessons = {
    "03_snapshot_screener": [
        md(
            "# U.S. bank screening with a frozen FDIC dataset\n\nLoad **4,313 institution financial records for 2026-06-30** with one call, then select a cohort using a stated reporting quarter. This frozen edition includes NC and OI classes; it is not an insured-only or active-only list, a list of banks for sale, or a latest-data claim. After installation all cells run offline.\n"
        ),
        code(install),
        code(
            'from usbankdata import snapshot\n\ndata = snapshot(quarter="2026Q2", edition="2026-q2-r1")\nassert len(data.rows) == 4313\nprint(data.dataset_id)\nprint(data.document["selection"]["scope"])\nprint(data.document["coverage"]["fields"]["cet1_ratio_pct"])\n'
        ),
        md(
            "## Select a population before comparing it\n\nFor this exercise select NC institutions in the N, SM, NM, SB, SI and SL classes, with assets **at least $100 million and below $3 billion** at 2026Q2. These filters are an example research choice, not an official FDIC peer group. Money columns are dollars; 12.5 in a ratio column means 12.5%, and ROA/ROE are already annualized.\n"
        ),
        code(
            'cohort = data.select(states=["NC"], bank_classes=["N", "SM", "NM", "SB", "SI", "SL"],\n                     min_assets_usd=100_000_000, max_assets_usd=3_000_000_000)\nassert cohort.certs\nassert cohort.document["selection"]["anchor_report_date"] == "2026-06-30"\nprint("Selected institutions:", len(cohort.certs))\nfor row in cohort.rows[:5]:\n    print(row["cert"], row["bank_name"], row["assets_usd"], row["cet1_ratio_pct"])\n'
        ),
        md(
            "## Derive one funding measure without filling missing data\n\nUse estimated uninsured **domestic** deposits divided by domestic deposits. Keep an absent numerator or nonpositive denominator missing. Do not replace this denominator with total deposits or treat this measure as a risk score. Derived results below are separate from the reported source fields.\n"
        ),
        code(
            'derived = []\nfor row in cohort.rows:\n    numerator, denominator = row["uninsured_deposits_usd"], row["domestic_deposits_usd"]\n    share = None if numerator is None or denominator is None or denominator <= 0 else 100 * numerator / denominator\n    derived.append({"cert": row["cert"], "uninsured_domestic_share_pct_derived": share})\nprint(derived[:5])\n'
        ),
        code(
            'from pathlib import Path\nfrom usbankdata import BankCohort\n\noutput = Path("outputs/snapshot-screener")\ncohort.export(output / "nc-banks.csv")\ncohort.export(output / "nc-banks.json")\nassert BankCohort.load(output / "nc-banks.json").rows == cohort.rows\nprint(output / "nc-banks.manifest.json")\n'
        ),
        md(
            "## Exercise\n\nChange the state and asset bounds. How does the number of selected institutions change? Count missing CET1 observations before comparing ratios. Keep the source manifest and state the selection anchor in your answer.\n\nSource: FDIC BankFind Suite; BanksOnSale compilation and metadata (CC BY 4.0), provided through US Bank Data. The archived source edition is as retrieved in October 2026, not the original filing vintage. [Definitions and population](https://github.com/anshuman-pandey/us-bank-data/blob/v0.2.0/docs/COHORTS.md).\n"
        ),
    ],
    "04_cohort_history": [
        md(
            "# One reporting window across several banks\n\nUse three **offline interface samples** for eight aligned quarters, 2024Q3 through 2026Q2. They have different sizes and business models; they are not a matched peer group or a population suitable for causal inference. Every selected bank has one row per requested quarter, even when a live filing is absent.\n"
        ),
        code(install),
        code(
            'from usbankdata import load_sample_cohort\n\ndata = load_sample_cohort()\nassert len(data.rows) == 24\nassert data.certs == [628, 3510, 58665]\nassert data.document["requested_dates"] == sorted(data.document["requested_dates"])\nprint(data.document["coverage"])\n'
        ),
        md(
            "## Compute a change only when both observations exist\n\nDo not substitute an older filing for a missing requested quarter. A missing source field is different from an absent filing, recorded by `report_available`. This example calculates deposit changes separately from the immutable reported values.\n"
        ),
        code(
            'for cert in data.certs:\n    bank_rows = [row for row in data.rows if row["cert"] == cert]\n    start, end = bank_rows[0]["deposits_usd"], bank_rows[-1]["deposits_usd"]\n    change = None if start is None or end is None else end - start\n    print(cert, bank_rows[-1]["bank_name"], "deposit change USD:", change)\n'
        ),
        code(
            'from pathlib import Path\nfrom usbankdata import BankCohort\n\noutput = Path("outputs/cohort-history")\ndata.export(output / "bank-quarter-panel.csv")\ndata.export(output / "bank-quarter-panel.json")\nassert BankCohort.load(output / "bank-quarter-panel.json").dataset_id == data.dataset_id\nprint(data.dataset_id)\n'
        ),
        md(
            '## Choose your own live banks\n\nThe following is optional and is intentionally not executed by this offline lesson:\n\n```python\nfrom usbankdata import panel\nlive = panel(certs=[628, 3510, 58665], through="2026Q2", quarters=8)\n```\n\nA live call supports up to 100 explicit CERTs and 40 quarters, with bounded pagination and retries. It retrieves current source revisions and identity labels. It does not silently filter out inactive banks. Select a cohort from a single-quarter snapshot first if state or size matters, and keep that snapshot selection manifest alongside the historical result. CERT identifies a bank institution, not its listed parent or ticker.\n'
        ),
        md(
            "## Exercise and solution direction\n\nAdd a missing-quarter check before calculating percentage growth. A valid solution returns missing when the first observation is absent or nonpositive, and keeps that result distinct from zero growth. Original source: FDIC BankFind Suite; BanksOnSale sample compilation and metadata, surfaced by US Bank Data. [Contract](https://github.com/anshuman-pandey/us-bank-data/blob/v0.2.0/docs/COHORTS.md).\n"
        ),
    ],
    "05_polars_duckdb_bank_data": [
        md(
            "# Analyze the same bank cohort with Polars and DuckDB\n\nA practical lazy-query and SQL lesson over a frozen 2026Q2 FDIC institution dataset. Use the same selected population and reporting date in both tools, compare results, and keep the source evidence with the exported Parquet. After installing the optional libraries, no source requests or account are needed.\n"
        ),
        code(teaching_install),
        code(
            'from pathlib import Path\nfrom usbankdata import snapshot\n\ndata = snapshot().select(bank_classes=["N", "SM", "NM", "SB", "SI", "SL"],\n                         min_assets_usd=100_000_000, max_assets_usd=3_000_000_000)\noutput = Path("outputs/polars-duckdb")\npath = data.export(output / "bank-cohort.parquet")\nassert data.rows\nprint("Institutions:", len(data.certs))\n'
        ),
        md(
            "## Join identities and group with Polars\n\nRead the Parquet lazily and join the source identity table by CERT, with a many-to-one validation. Group by the same report date and source state, aggregate accounting amounts in dollars, and count missing CET1 observations. A null-safe derived funding percentage is separate from the reported fields. Identity labels are as retrieved. Do not average bank ratios to represent an aggregate balance sheet. No ranking or sale availability is inferred.\n"
        ),
        code(
            'import polars as pl\n\nidentities = [{"cert": bank["cert"], "state": bank["state"]} for bank in data.banks]\nidentity_frame = pl.DataFrame(identities)\nframe = (pl.scan_parquet(path)\n    .join(identity_frame.lazy(), on="cert", how="left", validate="m:1")\n    .with_columns(pl.when(pl.col("domestic_deposits_usd") > 0)\n        .then(100 * pl.col("uninsured_deposits_usd") / pl.col("domestic_deposits_usd"))\n        .otherwise(None).alias("uninsured_share_pct_derived")))\npolars_result = (frame.group_by(["report_date", "state"]).agg(\n    pl.len().alias("institutions"),\n    pl.col("assets_usd").sum().alias("assets_usd"),\n    pl.col("cet1_ratio_pct").null_count().alias("missing_cet1")\n).sort(["report_date", "state"]).collect())\nprint(polars_result)\nassert polars_result["institutions"].sum() == len(data.certs)\nprint(frame.select("cert", "uninsured_share_pct_derived").head(5).collect())\n'
        ),
        md(
            "## Query the same file with DuckDB\n\nThe query uses a parameter for the file path. Read-only SQL keeps nulls intact. Compare counts, total assets and missing CET1 counts with Polars on exactly the same cohort.\n"
        ),
        code(
            'import duckdb\nimport pyarrow as pa\n\nconnection = duckdb.connect()\nconnection.register("identities", pa.Table.from_pylist(identities))\nsql_result = connection.execute("""\n    SELECT report_date, state, count(*) AS institutions, sum(assets_usd) AS assets_usd,\n           count(*) - count(cet1_ratio_pct) AS missing_cet1\n    FROM read_parquet(?) AS financials\n    LEFT JOIN identities USING (cert)\n    GROUP BY report_date, state\n    ORDER BY report_date, state\n""", [str(path)]).fetchall()\nconnection.close()\nassert sql_result == polars_result.rows()\nprint(sql_result[:5])\n'
        ),
        md(
            "## Verify the evidence embedded in Parquet\n\nRaw source responses, hashes, metric definitions, coverage and selection rules are stored under `usbankdata` in the Parquet schema metadata. Keep them when creating a new file; a generic dataframe rewrite can discard that metadata.\n"
        ),
        code(
            'import json\nimport pyarrow.parquet as pq\n\nreceipt = json.loads(pq.read_schema(path).metadata[b"usbankdata"])\nassert receipt["dataset_id"] == data.dataset_id\nassert receipt["selection"]["anchor_report_date"] == "2026-06-30"\nassert receipt["metric_definitions"]["assets_usd"]["unit"] == "USD"\nassert receipt["metric_definitions"]["cet1_ratio_pct"]["unit"] == "percent"\nprint(receipt["coverage"])\n'
        ),
        md(
            "## Exercise\n\nCompare deposits and assets for another explicit size range. Add a safe derived loans/assets measure while preserving missing fields and zero denominators. Ensure Polars and SQL use the same selection. Source: FDIC BankFind Suite; BanksOnSale compilation and metadata (CC BY 4.0), provided through US Bank Data. This is an as-retrieved dataset edition, not an original-filing vintage. [Population and units](https://github.com/anshuman-pandey/us-bank-data/blob/v0.2.0/docs/COHORTS.md).\n"
        ),
    ],
}

for name, cells in lessons.items():
    for number, cell in enumerate(cells):
        cell["id"] = f"cohort-{number:02d}"
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12.0"},
        },
        "cells": cells,
    }
    (ROOT / "notebooks" / f"{name}.ipynb").write_text(json.dumps(notebook, indent=1) + "\n")
print("Generated", len(lessons), "offline cohort lessons.")
