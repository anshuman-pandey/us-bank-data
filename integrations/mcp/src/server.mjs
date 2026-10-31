import {Server} from '@modelcontextprotocol/sdk/server/index.js';
import {WebStandardStreamableHTTPServerTransport} from '@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js';
import {CallToolRequestSchema,ListToolsRequestSchema} from '@modelcontextprotocol/sdk/types.js';
import {CfWorkerJsonSchemaValidator} from '@modelcontextprotocol/sdk/validation/cfworker';
import {INSTRUCTIONS} from './catalog.mjs';
import {createTools} from './tools.mjs';

/** @param {() => Promise<any>} getDataset @param {Parameters<typeof createTools>[1]} options */
export function createServer(getDataset,options={}) {
  const tools=createTools(getDataset,options);
  const server=new Server({name:'us-bank-data',version:'0.1.0',title:'US Bank Data',websiteUrl:'https://www.banksonsale.com/ai'},{capabilities:{tools:{}},instructions:INSTRUCTIONS,jsonSchemaValidator:new CfWorkerJsonSchemaValidator()});
  server.setRequestHandler(ListToolsRequestSchema,async()=>({tools:tools.list()}));
  server.setRequestHandler(CallToolRequestSchema,async request=>tools.call(request.params.name,request.params.arguments??{}));
  return server;
}

const ALLOWED_ORIGINS=new Set(['https://www.banksonsale.com','https://banksonsale.com','https://chatgpt.com','https://claude.ai','https://banks-on-sale.sunshinevendetta.chatgpt.site']);
const rpc=(id,result,status=200)=>Response.json({jsonrpc:'2.0',id,result},{status});

/** @param {() => Promise<any>} getDataset @param {Parameters<typeof createTools>[1]} options */
export function createHttpHandler(getDataset,options={}) {
  const tools=createTools(getDataset,options);
  return async function handle(request) {
    const origin=request.headers.get('origin');
    const url=new URL(request.url);
    const local=url.hostname==='127.0.0.1'||url.hostname==='localhost';
    if(origin&&!ALLOWED_ORIGINS.has(origin)&&!(local&&/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)))return new Response('Origin not allowed',{status:403});
    const headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Vary':'Origin'};
    if(origin){headers['Access-Control-Allow-Origin']=origin;headers['Access-Control-Allow-Headers']='Content-Type, Accept, MCP-Protocol-Version, MCP-Session-Id';headers['Access-Control-Allow-Methods']='POST, GET, OPTIONS';}
    if(request.method==='OPTIONS')return new Response(null,{status:204,headers});
    // GET is deliberately 405: this stateless, read-only server has no SSE
    // subscriptions. The install guide is /ai, not the protocol endpoint.
    if(request.method!=='POST')return new Response('Use MCP POST; setup guide: https://www.banksonsale.com/ai',{status:405,headers:{...headers,Allow:'POST, OPTIONS'}});
    const bodyLimit=16384;
    if(Number(request.headers.get('content-length')??0)>bodyLimit)return new Response('Request too large',{status:413,headers});
    const reader=request.body?.getReader();let size=0;const chunks=[];
    if(!reader)return new Response('Missing request body',{status:400,headers});
    try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>bodyLimit){await reader.cancel();return new Response('Request too large',{status:413,headers});}chunks.push(value);}}finally{reader.releaseLock();}
    const bytes=new Uint8Array(size);let pos=0;for(const c of chunks){bytes.set(c,pos);pos+=c.length;}
    let body;try{body=JSON.parse(new TextDecoder().decode(bytes));}catch{return Response.json({jsonrpc:'2.0',id:null,error:{code:-32700,message:'Parse error'}},{status:400,headers});}
    if(Array.isArray(body)||!body||typeof body!=='object'||body.jsonrpc!=='2.0')return Response.json({jsonrpc:'2.0',id:null,error:{code:-32600,message:'Invalid request'}},{status:400,headers});
    let response;
    // Sites' managed connector currently discovers via MCP 2026-07-28.
    // Public ChatGPT/Claude clients use the SDK-negotiated 2025-11-25 transport.
    if(body.method==='server/discover'&&body.id!==undefined){response=rpc(body.id,{supportedVersions:['2026-07-28','2025-11-25'],capabilities:{tools:{}},serverInfo:{name:'us-bank-data',version:'0.1.0'},instructions:INSTRUCTIONS});}
    else if(request.headers.get('MCP-Protocol-Version')==='2026-07-28'&&['tools/list','tools/call'].includes(body.method)&&body.id!==undefined){
      response=rpc(body.id,body.method==='tools/list'?{tools:tools.list()}:await tools.call(body.params?.name,body.params?.arguments??{}));
    }else{
      const server=createServer(getDataset,options);
      const transport=new WebStandardStreamableHTTPServerTransport({sessionIdGenerator:undefined,enableJsonResponse:true,maxRequestBodySize:bodyLimit});
      try{await server.connect(transport);response=await transport.handleRequest(new Request(request.url,{method:'POST',headers:request.headers,body:bytes}),{parsedBody:body});}
      finally{await server.close();}
    }
    for(const [key,value] of Object.entries(headers))response.headers.set(key,value);
    return response;
  };
}
