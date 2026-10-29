# Contributing to BanksOnSale Data

Useful contributions improve the correctness or usability of sourced U.S. bank
research. Include a reproducible example, the affected FDIC CERT/reporting period,
field definitions and source evidence when proposing a data correction.

## Local verification

Python 3.10+:

```bash
python -m venv .venv
# Activate your environment, then:
python -m pip install -e .
python -m unittest discover -s tests -v
```

Optional export checks run when pandas/pyarrow/Polars are installed. The core
must continue to work with the standard library. Changes to metric mapping,
units, null handling, institution identity or quarter selection need a regression
case. Do not put credentials, business records, account exports or private
BanksOnSale application code into this repository.

## Samples and notebooks

Samples are real archived FDIC observations, not invented rows. The example is
explicitly pinned to 2026Q2. Do not silently refresh a released sample. A new
edition requires updated source evidence, coverage review, notebook output,
manifest and version notes. `scripts/refresh_samples.py` is an explicit
network-using maintainer action, excluded from ordinary CI.

Notebook changes should run in a clean kernel. Keep a small offline path, label
the report dates, retain source evidence and avoid implying a matched peer group
when the example simply demonstrates banks of different sizes.

## Public integrations and listings

An upstream contribution must help the receiving project, comply with its own
contribution guidance and disclose the BanksOnSale relationship. No unsolicited
promotional issues, mass link submissions, tracking parameters in curated-list
entries, or claims of official endorsement. An optional integration does not
make BanksOnSale a default dependency of the upstream project.
