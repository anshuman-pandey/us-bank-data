# BanksOnSale for OpenBB

An independently maintained extension from [BanksOnSale](https://banksonsale.com). It adds
`obb.banksonsale` to OpenBB V5. It is not an official or bundled OpenBB provider.

Install the data package first, then the extension, from this repository:

```bash
python -m pip install 'banksonsale-data[io] @ git+https://github.com/anshuman-pandey/banksonsale-data.git@v0.1.0'
python -m pip install 'openbb-banksonsale @ git+https://github.com/anshuman-pandey/banksonsale-data.git@v0.1.0#subdirectory=integrations/openbb'
openbb-build
```

For development, install the root with `pip install -e '.[io]'`, then run
`pip install -e integrations/openbb` and `openbb-build` in the same environment.

```python
from openbb import obb

example = obb.banksonsale.sample(cert=58665)  # offline, real source-archived data
example.to_dataframe()
example.extra["banksonsale"]["metric_definitions"]

# These two calls access the public FDIC API:
obb.banksonsale.lookup(name="Live Oak", state="NC")
result = obb.banksonsale.financials(cert=58665, quarters=8)
result.to_dataframe()
```

The same commands are available under `/api/v1/banksonsale/` in an OpenBB API
environment with the extension installed. Source archives, coverage, dataset identity,
and metric definitions travel in `extra.banksonsale`.

Financials are for the selected FDIC bank, not its listed holding company. Monetary
columns are USD, ratios are percentage points, and missing reports stay missing.
See the root [data contract](../../docs/DATA_CONTRACT.md).

Integration reference: [OpenBB V5 router extensions](https://docs.openbb.co/odp/python/developer/extension_types/router).
