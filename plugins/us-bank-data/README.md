# US Bank Data for ChatGPT and Claude

Ask about U.S. bank financials and get reporting dates, units and source links.
No account, API key, Python installation or subscription is needed for the
public hosted connector. Your AI provider's plan and workspace rules still apply.

- **MCP URL:** `https://www.banksonsale.com/api/mcp`
- **Authentication:** none
- **Transport:** Streamable HTTP
- **Guide:** https://www.banksonsale.com/ai

## Connect in ChatGPT

Open **Plugins → + → Add custom MCP server**. Name it **US Bank Data**, paste
the MCP URL, and choose no authentication. Install the resulting plugin and
enable it in a new conversation. Workspace permissions may restrict who can
add custom servers. Public directory inclusion requires a separate submission
and review; this repository does not imply OpenAI approval.

## Connect in Claude

Open **Customize → Connectors → Add custom connector**, enter **US Bank Data**
and the MCP URL, and choose **No sign in** when prompted. Team or Enterprise
admins may need to add it first. Exact menus and plan availability can change;
see [Claude's official setup guide](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

For Claude Code, add our self-hosted marketplace and install:

```sh
claude plugin marketplace add anshuman-pandey/us-bank-data
claude plugin install us-bank-data@us-bank-data-tools
```

Or connect only the remote server:

```sh
claude mcp add --transport http us-bank-data https://www.banksonsale.com/api/mcp
```

Our marketplace is independent. It is not a listing in Anthropic's directory.

## Try it

- “Find State Street Bank and show its frozen June 2026 financials.”
- “Compare CERT 14 and 3510 at June 30, 2026, with source links.”
- “Find North Carolina banks with $100 million to $1 billion in assets.”
- “What is the latest available FDIC financial observation for CERT 628?”
- “Explain the difference between CET1 and the leverage ratio.”

The eight read-only tools are `search`, `fetch`, `get_dataset_info`,
`get_bank_financials`, `compare_banks`, `screen_banks`,
`get_metric_definitions` and `get_live_bank_financials`.

## Data contract

The reproducible edition contains **4,313 records for June 30, 2026**, with 14
financial fields. NC noninsured institutions and OI insured U.S. branches of
foreign institutions are included. There is no implicit insured-only or
active-only filter. It is not a sale listing or a complete bank-history database.
Live lookup calls FDIC at request time; it reports the actual returned quarter
and can differ from the frozen edition. Live prior quarters can be revised.

MCP monetary fields ending `_usd` are already **U.S. dollars**; source website
downloads retain **USD thousands**. `_pct` fields are percentages, not fractions.
Missing values remain null. FDIC CERT identifies an institution, not a parent
company or branch. Credit unions, consumer accounts and private workspace data
are not available through this connector.

## Privacy Policy

The remote server receives only the selected tool's arguments: bank names,
CERTs, filters or public-document IDs. It does not require an email address,
login, payment information or customer account credentials. Live lookup sends
the CERT and requested quarter to FDIC. Frozen queries use the public snapshot.
The application does not intentionally persist tool queries or results; hosting
providers process request metadata under their service policies. Normal website
analytics can apply when you visit the documentation pages. Do not submit
confidential information. See the [connector privacy notice](https://www.banksonsale.com/ai/privacy)
and [website policy](https://www.banksonsale.com/privacy).

## Source and license

Code and plugin instructions: MIT, see LICENSE. BanksOnSale compilation and
original metadata: CC BY 4.0, with FDIC BankFind Suite as the original source.
Neither FDIC, OpenAI nor Anthropic endorses this independent project. Cite the
returned bank/report-date URL and the frozen edition or live retrieval details.

Source: https://github.com/anshuman-pandey/us-bank-data

Issues: https://github.com/anshuman-pandey/us-bank-data/issues
