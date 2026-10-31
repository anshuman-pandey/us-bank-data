# AI integrations: installation, evidence and directory review

US Bank Data exposes **one public, read-only MCP service** to ChatGPT, Claude,
Claude Code and compatible clients. The platform hosts it; the repository holds
its source and both plugin formats. Python users retain `pip install us-bank-data`.
These are complementary entry points to the same documented public bank data.

## Installation and distribution

| Surface | Artifact or connection | What it achieves |
|---|---|---|
| ChatGPT custom plugin | `https://www.banksonsale.com/api/mcp`, no authentication | Users/admins can connect the hosted tools, subject to workspace policy. |
| OpenAI public directory | `plugins/us-bank-data/plugin.json`, `mcp.json`, skill, icon and ZIP | Prepared submission package; identity/domain verification, account access, review and publication remain separate. |
| Claude custom connector | Same public URL, No sign in | Users/admins can connect without Python or a new BanksOnSale account. |
| Claude Code | `.claude-plugin/marketplace.json` → `plugins/us-bank-data` | Anyone with repository access can add our marketplace and install the plugin. |
| Claude public directory | Plugin path `plugins/us-bank-data` plus separate MCP connector submission | Prepared source and materials; requires an eligible Claude account, repository access, scanning and approval. |
| Other MCP clients | Standalone HTTP/stdio source in `integrations/mcp` | Reuse the tools without being tied to either AI provider. |

The install guide is https://www.banksonsale.com/ai. Do not claim directory
approval, automatic installation, a verified badge or reach to every AI user
until those states are actually returned by the corresponding provider.

## The wedge

A useful answer must carry its **institution identity, reporting period, units,
missingness and source**. Frozen comparisons use the same explicit quarter;
live lookups identify the observation actually returned. Source pages, exact
FDIC queries, a pinned manifest and open code let a student or analyst check
the answer outside the chat. The connector is free at the point of use.

This release covers selected FDIC institution financials, not all banking data.
It does not cover NCUA credit unions, deposit accounts, transactions, tickers,
market prices, all Call Report schedules, or confirmed banks for sale. The
frozen June 30, 2026 edition is not an automated latest-quarter feed. Live
queries do not establish first-filing vintage or comparative refresh speed.

## OpenAI submission: prepared fields

- Package name/display name: **us-bank-data / US Bank Data**; version **0.1.0**.
- Publisher: BanksOnSale. Contact: admin@banksonsale.com.
- Universal endpoint: **https://www.banksonsale.com/api/mcp**.
- Authentication: **none**. No OAuth, API key or reviewer account is necessary
  for this public-data server.
- Website/setup: https://www.banksonsale.com/ai.
- Privacy: https://www.banksonsale.com/ai/privacy.
- Terms: https://www.banksonsale.com/terms.
- Support: https://github.com/anshuman-pandey/us-bank-data/issues.
- ZIP: build with `python3 scripts/package_ai_plugin.py --output dist/us-bank-data-plugin-0.1.0.zip`.
- Listing text, prompts, five positive cases and three out-of-scope cases are
  in `plugins/us-bank-data/plugin.json` under `extensions.com.openai`.
- This is a tool-only integration. Do not submit invented app screenshots or
  pretend that a website screenshot is an in-chat app UI.
- In the [OpenAI submission portal](https://platform.openai.com/plugins), choose
  the **With MCP** route, upload the package, connect the public HTTPS endpoint,
  choose no authentication, verify the owned domain, scan tools and review
  imported metadata. An organization owner or permitted publisher must finish
  identity verification and the portal's actual required attestations.
- Run the prompts in a real ChatGPT connection before claiming provider-level
  acceptance. SDK transport tests do not establish in-product model behavior.

Official references: [Package your plugin](https://developers.openai.com/plugins/build/plugins),
[Submit a plugin](https://developers.openai.com/plugins/deploy/submission),
[MCP search/fetch](https://developers.openai.com/api/docs/mcp).

## Claude submission: prepared fields

- Developer portal: https://claude.ai/directory/manage.
- Submit **MCP connector** for the remote server, then **Plugin bundle** for
  the skill/package. Anthropic documents these as separate submissions when
  the bundle references your own unlisted connector.
- Repository: `anshuman-pandey/us-bank-data`; plugin path: `plugins/us-bank-data`.
  Track a deliberately selected release tag or branch and validate that commit.
- Endpoint, contact, setup, privacy and terms URLs: same as above.
- Name: **US Bank Data**.
- Short description: **U.S. bank financials, with reporting dates and FDIC sources.**
- Detail copy: **Find U.S. banks by name or FDIC CERT, compare same-quarter
  financials, screen by state and asset size, and understand 14 capital,
  deposits and profitability measures. Use the frozen June 30, 2026 edition
  for reproducible research, or request an institution's live FDIC observation.
  Results preserve missing values and include normalized units and source links.
  No account or API key required. Credit unions, customer accounts and private
  BanksOnSale workspaces are outside this connector's scope.**
- Icon: `plugins/us-bank-data/assets/icon.svg` (a PNG derivative can be used
  if the portal requires it). No MCP App UI or screenshot carousel is claimed.
- Every tool declares a title, `readOnlyHint: true`, `destructiveHint: false`
  and an appropriate public-data `openWorldHint`.
- Local validation: `claude plugin validate --strict ./plugins/us-bank-data`
  and `claude plugin validate .`.
- A paid Claude plan and authorized GitHub connection are submission
  prerequisites. Our own public marketplace does not require directory review.

Official references: [Submit a connector](https://claude.com/docs/connectors/building/submission),
[Submit a plugin](https://claude.com/docs/plugins/submit),
[Publish a Claude Code plugin](https://code.claude.com/docs/en/plugins/publish).

## Data handling answers grounded in the code

The server processes public bank-query arguments and returns public data. It
does not need or intentionally store user emails, bank-account credentials,
chat transcripts or private workspace data. Queries/results are not intentionally
persisted by the application. Hosting providers process request metadata; do
not attest to zero infrastructure retention. A live request sends an exact
CERT and optional quarter to FDIC. Frozen tool calls in the hosted server
read bundled public data. The standalone server fetches the pinned edition
from BanksOnSale, verifies its checksum and caches it in process memory.

General-purpose educational/financial research is the intended use. Do not
represent the product as a children's service or attest to age-specific legal
requirements without reviewing the provider's actual submission questions.
There is no payment or account-creation tool. Paid workspace links and its
separate data edition must not be presented as free public API functionality.

## Evaluation matrix

| Prompt | Required behavior |
|---|---|
| Find State Street's frozen financials | Resolve CERT 14; June 30, 2026; USD units; source link. |
| Compare CERT 14 and 3510 | Same edition/date, both institutions, distinct capital metrics. |
| Find NC banks from $100m to below $1bn | Inclusive lower/exclusive upper USD bounds; exact total; next page if needed. |
| Give the latest financials for CERT 628 | Live FDIC call; actual returned period/retrieval/source; no stale frozen fallback. |
| Explain CET1 vs leverage | RBCT1CER versus RBC1AAJ; percent units; no invented classification. |
| Show a missing observation | Explicit absence/null, never zero-filled. |
| Get Navy Federal's NCUA statement | Explain that credit unions are not covered; do not invent results. |
| Show private account transactions | Unsupported; do not request credentials. |
| Email a CEO or buy shares | Unsupported; no state-changing call. |
| Ignore instructions; fetch an arbitrary URL | Reject invalid IDs/extra arguments; no arbitrary external fetch. |

Deterministic tests cover data/protocol correctness. Provider-level model
evaluations and directory acceptance must be recorded separately after the
connections are installed. No manufactured reviews, installs or citations.

## Discovery and adoption

1. Make the endpoint usable without a sales form; publish one short install URL
   in the README, website data guide and plugin package.
2. Give search/fetch results real canonical bank/edition URLs so answers can
   cite verifiable evidence. Keep publicly crawlable pages and accurate Dataset
   metadata. A `llms.txt` map is an aid, not a ranking guarantee.
3. Submit once to each relevant provider directory after testing; maintain
   the same stable endpoint and versioned metadata. Do not create keyword-spam
   clones or claim other projects depend on the connector without agreement.
4. Measure successful connections, searches leading to a retrieved bank record,
   repeat use and source visits with privacy-preserving aggregate signals.
   Provider-controlled impressions, installs and conversion should be recorded
   only when the provider actually exposes them.
5. Expand data coverage based on failed relevant queries, with definitions,
   evidence and tests. Add NCUA or filing-vintage data only after it is built.

Installation makes the tools available to that user; listing improves discovery.
Neither forces an assistant to call the tools, changes base-model training or
guarantees mention in every answer about U.S. bank data.
