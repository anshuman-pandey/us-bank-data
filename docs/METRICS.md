# BanksOnSale Data metric definitions

The package normalizes source monetary observations to USD. The website's raw FDIC downloads retain USD thousands; check the format before joining.

| Package column | FDIC field | Package unit | Multiplier | Basis |
| --- | --- | --- | --- | --- |
| `assets_usd` | `ASSET` | USD | 1000 | period_end |
| `deposits_usd` | `DEP` | USD | 1000 | period_end |
| `domestic_deposits_usd` | `DEPDOM` | USD | 1000 | period_end |
| `equity_usd` | `EQ` | USD | 1000 | period_end |
| `intangibles_usd` | `INTAN` | USD | 1000 | period_end |
| `net_loans_usd` | `LNLSNET` | USD | 1000 | period_end |
| `uninsured_deposits_usd` | `DEPUNINS` | USD | 1000 | period_end |
| `core_deposits_usd` | `COREDEP` | USD | 1000 | period_end |
| `cet1_ratio_pct` | `RBCT1CER` | percent | 1 | period_end |
| `leverage_ratio_pct` | `RBC1AAJ` | percent | 1 | period_end |
| `roa_pct` | `ROA` | percent | 1 | annualized_by_source |
| `roe_pct` | `ROE` | percent | 1 | annualized_by_source |
| `domestic_offices` | `OFFDOM` | count | 1 | period_end |
| `employees` | `NUMEMP` | count | 1 | period_end |

Original definitions: https://api.fdic.gov/banks/docs/risview_properties.yaml

Null observations are never converted to zero. Ratio values are already percentages. See [the data contract](DATA_CONTRACT.md) for time and identity rules.
