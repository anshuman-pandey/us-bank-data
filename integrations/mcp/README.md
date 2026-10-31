# US Bank Data MCP server

Eight read-only tools for ChatGPT, Claude, Claude Code and compatible MCP clients.
The public hosted endpoint is **https://www.banksonsale.com/api/mcp**. No key,
sign-in or package install is needed to connect. Start with the
[installation guide](https://www.banksonsale.com/ai) or [plugin package](../../plugins/us-bank-data).

## Run the source yourself

Node.js 22 or newer:

```sh
git clone https://github.com/anshuman-pandey/us-bank-data.git
cd us-bank-data/integrations/mcp
npm ci --ignore-scripts
npm start
```

This starts a loopback-only server at `http://127.0.0.1:3333/mcp`. It downloads
the pinned public edition on the first frozen-data query, verifies its SHA-256
and holds it in memory. Live queries go directly to FDIC. No OpenAI or Anthropic
API calls, model keys, telemetry, database, browser cookies or account sessions
are used. Do not expose the loopback development server as a production service
without your deployment's access/rate-limit controls.

For a client that starts local stdio servers:

```json
{
  "mcpServers": {
    "us-bank-data": {
      "command": "node",
      "args": ["/absolute/path/to/us-bank-data/integrations/mcp/src/stdio.mjs"]
    }
  }
}
```

The client must use an absolute path after cloning and running `npm ci`.
The hosted remote URL works directly in Claude without this local setup.

## Embed in a Fetch-compatible host

```js
import {createHttpHandler} from './src/server.mjs';
import {loadPublicSnapshot} from './src/data.mjs';

let dataset;
const handle = createHttpHandler(() => dataset ??= loadPublicSnapshot().catch(e => {
  dataset = undefined;
  throw e;
}));
// Pass the incoming Request to handle(request); return its Response.
```

The website embeds the same source files and injects its bundled public edition,
so frozen tool calls do not download a file per request. No protected workspace
APIs are called. `/api/mcp` is the universal public endpoint; Sites' managed
owner/workspace connection uses `/mcp` and its own hosting authentication.

## Protocol and limits

- Official TypeScript MCP SDK 1.32.2; stateless Streamable HTTP with JSON responses.
- SDK negotiates MCP 2025-11-25 and its supported previous versions. A bounded
  `server/discover`/tools compatibility path supports Sites' MCP 2026-07-28 client.
- Eight tools, strict JSON Schema argument validation and read-only annotations.
- Origin allowlist; 16 KiB request ceiling; no arbitrary URL fetching.
- Up to 10 banks per frozen comparison; 100 screened records per response,
  stable CERT pagination and an exact total. No implicit insured/active filter.
- FDIC live requests: one exact CERT, optional exact quarter, 12-second timeout,
  100 KB response ceiling, numeric field/date/CERT validation. No fabricated
  fallback when the source is down or a field is missing.
- Frozen files: pinned checksum, 2.5 MB JSON ceiling, population/date/metric
  validation. Website source observations retain USD thousands; tool outputs
  multiply monetary values once into USD, as the Python package does.
- `search(query)` and `fetch(id)` follow ChatGPT's citation-compatible document
  contract and return canonical, human-readable public URLs.
- No writes, emails, purchases, confidential uploads or user-account access.

## Validate

From the repository root:

```sh
python3 scripts/prepare_mcp_fixture.py
npm ci --ignore-scripts --prefix integrations/mcp
npm test --prefix integrations/mcp
python3 scripts/package_ai_plugin.py --output dist/us-bank-data-plugin-0.1.0.zip
```

The tests use original responses bundled with the existing Python snapshot,
not invented bank fixtures. They cover numerical units and missingness, source
integrity, filtering, unsafe inputs, FDIC error/mismatch handling, protocol
initialization/discovery, and an official SDK client over a loopback HTTP server.
Normal tests do not depend on FDIC uptime. See [review and publication details](../../docs/AI_INTEGRATIONS.md).

## Privacy and license

See the [connector privacy notice](https://www.banksonsale.com/ai/privacy),
[plugin README](../../plugins/us-bank-data/README.md#privacy-policy),
[MIT code license](../../LICENSE) and [dataset license](../../DATA_LICENSE.md).
This integration is independent of FDIC, OpenAI and Anthropic.
