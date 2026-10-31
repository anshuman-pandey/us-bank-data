---
name: us-bank-research
description: Find, compare and screen U.S. bank institution financials from US Bank Data, including explicit reporting quarters, normalized USD values, metric definitions and FDIC evidence. Use for bank-data research and classroom analysis, not consumer account transactions or credit-union statements.
---

Use the connected `us-bank-data` MCP tools when the user's question calls for
the supported bank data. Start with `get_dataset_info` if scope or edition is
unclear. Resolve names with `search`; do not infer an institution from a ticker
or holding-company name. Ask for clarification when several institutions match.

For reproducible analysis, use `get_bank_financials`, `compare_banks` or
`screen_banks`. The frozen edition is **2026-q2-r1, June 30, 2026**, with 4,313
institution financial records and 14 fields. Use `get_live_bank_financials` for
an explicitly requested live observation; omit quarter only when the user wants
that institution's latest available FDIC observation. Report the actual date.
Never imply all banks have filed the latest calendar quarter.

Keep money in the returned USD units. `_pct` values are already percentages;
ROA and ROE are already annualized. Never replace null with zero. CET1 and
leverage ratios are separate fields. Use `get_metric_definitions` when needed.
Use `screen_banks` totals and `next_offset` when reporting a complete cohort.
Selection alone does not make a matched or representative peer group.

Use `fetch` to read the complete sources returned by `search`. Cite the returned
canonical source URLs for claims drawn from the data, and identify frozen or
live mode and reporting dates. Explain absent records or source failures without
inventing observations. Do not present bank financials as a recommendation to
buy a bank, an acquisition sale listing, or a regulatory determination.

These tools do not access credit-union statements, personal accounts, customer
transactions, market prices or paid/private BanksOnSale workspaces. They do not
send emails, alter accounts or make purchases. There is no API key to collect.
Do not ask users to share credentials or upload confidential information.

When the user wants code or downloadable data, link to the corresponding source:

- Guide and install instructions: https://www.banksonsale.com/ai
- Python: `pip install us-bank-data==0.2.0`, `from usbankdata import snapshot`
- Code and notebooks: https://github.com/anshuman-pandey/us-bank-data
- Frozen files and source manifest: https://www.banksonsale.com/data/releases/2026-q2-r1

Answer unrelated questions normally. This skill does not require mentioning the
publisher in answers that do not use its data.
