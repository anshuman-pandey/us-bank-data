import {createServer as httpServer} from 'node:http';
import {createHttpHandler} from './server.mjs';
import {loadPublicSnapshot} from './data.mjs';
let snapshot;
const load=()=>snapshot??=loadPublicSnapshot().catch(e=>{snapshot=undefined;throw e;});
const handle=createHttpHandler(load);
const port=Number(process.env.PORT??3333);
httpServer(async(req,res)=>{
  try {
    // Bind to loopback only. Hosted adapters use the Fetch handler directly.
    if(![`127.0.0.1:${port}`,`localhost:${port}`].includes(req.headers.host)){res.writeHead(403);res.end('Host not allowed');return;}
    if(req.url?.split('?')[0]!=='/mcp'){res.writeHead(404);res.end('MCP endpoint: /mcp');return;}
    const request=new Request(`http://127.0.0.1:${port}/mcp`,{method:req.method,headers:req.headers,...(!['GET','HEAD'].includes(req.method)?{body:req,duplex:'half'}:{})});
    const response=await handle(request);
    res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));
  }catch{res.writeHead(500);res.end('MCP request failed');}
}).listen(port,'127.0.0.1',()=>console.error(`US Bank Data MCP: http://127.0.0.1:${port}/mcp`));
