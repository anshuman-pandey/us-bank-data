import {StdioServerTransport} from '@modelcontextprotocol/sdk/server/stdio.js';
import {createServer} from './server.mjs';
import {loadPublicSnapshot} from './data.mjs';
let snapshot;
await createServer(()=>snapshot??=loadPublicSnapshot().catch(e=>{snapshot=undefined;throw e;})).connect(new StdioServerTransport());
