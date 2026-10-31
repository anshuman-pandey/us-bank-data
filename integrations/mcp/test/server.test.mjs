import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer as httpServer} from 'node:http';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StreamableHTTPClientTransport} from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import {createHttpHandler} from '../src/server.mjs';
import {createTools,TOOLS} from '../src/tools.mjs';
import {loadPublicSnapshot,validateSnapshot,liveBank} from '../src/data.mjs';

const rows=JSON.parse(await readFile(new URL('./fixtures/financials.json',import.meta.url)));
const manifest=JSON.parse(await readFile(new URL('./fixtures/manifest.json',import.meta.url)));
const dataset=validateSnapshot(rows,manifest);
const tools=createTools(async()=>dataset);
const result=async(name,args)=>{const r=await tools.call(name,args);assert.ok(!r.isError,JSON.stringify(r));return r.structuredContent;};
const request=(body,headers={})=>new Request('https://www.banksonsale.com/api/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream',...headers},body:JSON.stringify(body)});
const rpc=(method,params={})=>({jsonrpc:'2.0',id:1,method,params});
const handler=createHttpHandler(async()=>dataset);
const raw=d=>({...Object.fromEntries(Object.entries(d).filter(([k])=>/^[A-Z0-9]+$/.test(k))),CERT:d.cert,RSSDID:d.rssd_id,NAMEFULL:d.name,NAME:d.source_short_name,CITY:d.city,STALP:d.state,BKCLASS:d.bank_class,ACTIVE:d.active_in_source,REPDTE:20260630});
const fdic=(d,count=1)=>async()=>Response.json({totals:{count},data:count?[{data:d}]:[],meta:{index:{name:'fixture'}}});

test('frozen snapshot has a unique, explicit population and reporting date',()=>{
  assert.equal(dataset.rows.length,4313);
  assert.throws(()=>validateSnapshot([...rows.slice(0,-1),rows[0]],manifest),/duplicate/);
  assert.throws(()=>validateSnapshot(rows.slice(1),manifest),/population/);
});
test('dataset coverage never calls a frozen snapshot latest',async()=>{
  const info=await result('get_dataset_info',{});assert.equal(info.is_latest,false);assert.equal(info.record_count,4313);assert.equal(info.report_date,'2026-06-30');assert.equal(info.metrics.length,14);
});
test('money is converted once; ratios, null and negative values remain distinct',async()=>{
  const r=rows.find(x=>x.RBCT1CER===null&&x.ROA<0);assert.ok(r);
  const b=await result('get_bank_financials',{cert:r.cert});assert.equal(b.values.assets_usd,r.ASSET*1000);assert.equal(b.values.cet1_ratio_pct,null);assert.equal(b.values.roa_pct,r.ROA);assert.equal(b.units.assets_usd,'USD');assert.equal(b.provenance.citation_url,`https://www.banksonsale.com/banks/${r.cert}`);
});
test('CERT lookup does not guess ticker or inaccessible banks',async()=>{
  assert.equal((await result('get_bank_financials',{cert:999999})).found,false);
  for(const args of [{cert:'JPM'},{cert:1.2},{cert:0},{cert:628,edition:'latest'},{cert:628,api_key:'secret'}])assert.equal((await tools.call('get_bank_financials',args)).isError,true);
});
test('comparison retains every request, including explicit missing institutions',async()=>{
  const r=await result('compare_banks',{certs:[rows[0].cert,999999]});assert.equal(r.banks.length,2);assert.equal(r.banks[1].found,false);
  assert.equal((await tools.call('compare_banks',{certs:[14,14]})).isError,true);
  assert.equal((await tools.call('compare_banks',{certs:Array.from({length:11},(_,i)=>i+1)})).isError,true);
});
test('asset bounds are inclusive/exclusive in USD and pagination is stable',async()=>{
  const chosen=rows[0],amount=chosen.ASSET*1000;
  const r=await result('screen_banks',{min_assets_usd:amount,max_assets_usd:amount+1});assert.ok(r.banks.some(x=>x.cert===chosen.cert));
  const excluded=await result('screen_banks',{max_assets_usd:amount,states:[chosen.state]});assert.ok(!excluded.banks.some(x=>x.cert===chosen.cert));
  const a=await result('screen_banks',{limit:2}),b=await result('screen_banks',{limit:2,offset:a.next_offset});assert.equal(a.total,4313);assert.ok(a.banks[1].cert<b.banks[0].cert);
  assert.equal((await tools.call('screen_banks',{min_assets_usd:5,max_assets_usd:2})).isError,true);
  assert.equal((await tools.call('screen_banks',{states:['XX']})).isError,true);
  assert.equal((await tools.call('screen_banks',{limit:101})).isError,true);
});
test('screening keeps NC and OI unless explicitly filtered',async()=>{
  const r=await result('screen_banks',{bank_classes:['NC']});assert.equal(r.total,66);
  assert.equal((await result('screen_banks',{bank_classes:['OI']})).total,9);
  assert.equal((await result('screen_banks',{states:['AK'],bank_classes:['NC']})).total,0);
});
test('standard search/fetch yields citable source documents, not arbitrary URLs',async()=>{
  const s=await result('search',{query:'State Street'});assert.ok(s.results.some(x=>x.id==='bank:14'));
  const f=await result('fetch',{id:'bank:14'});assert.equal(f.id,'bank:14');assert.ok(JSON.parse(f.text).values.assets_usd>0);assert.equal(f.url,'https://www.banksonsale.com/banks/14');
  assert.equal((await result('search',{query:'zzzznonexistentbankzzzz'})).results.length,0);
  assert.ok((await result('search',{query:"What are JPMorgan Chase's total assets?"})).results.some(x=>x.id==='bank:628'));
  assert.ok((await result('search',{query:'FDIC CERT 14'})).results.some(x=>x.id==='bank:14'));
  for(const id of ['https://example.com','bank:1:2','bank:999999','bank:0014'])assert.equal((await tools.call('fetch',{id})).isError,true);
});
test('metric lookup distinguishes CET1 and leverage and searches definitions',async()=>{
  const m=await result('get_metric_definitions',{fields:['RBCT1CER','RBC1AAJ']});assert.equal(m.metrics.length,2);assert.notEqual(m.metrics[0].key,m.metrics[1].key);
  assert.ok((await result('search',{query:'CET1'})).results.some(r=>r.id==='metric:RBCT1CER'));
  assert.equal((await result('fetch',{id:'dataset:2026-q2-r1'})).id,'dataset:2026-q2-r1');
});
test('live lookup reports actual quarter, retrieval time and exact source query',async()=>{
  const b=await liveBank(14,'2026Q2',fdic(raw(rows[0])));assert.equal(b.found,true);assert.equal(b.values.assets_usd,rows[0].ASSET*1000);assert.equal(b.provenance.mode,'live');assert.equal(b.report_date,'2026-06-30');assert.match(b.provenance.source_url,/CERT%3A14/);assert.ok(b.provenance.retrieved_at);
});
test('live lookup rejects inconsistent, incomplete and wrong-quarter data',async()=>{
  await assert.rejects(()=>liveBank(15,'2026Q2',fdic(raw(rows[0]))),/mismatch/);
  await assert.rejects(()=>liveBank(14,'2026Q1',fdic(raw(rows[0]))),/quarter/);
  const missing=raw(rows[0]);delete missing.ROA;await assert.rejects(()=>liveBank(14,'2026Q2',fdic(missing)),/metric/);
  assert.equal((await liveBank(14,'2026Q2',fdic({},0))).found,false);
  const safe=createTools(async()=>dataset,{fetcher:fdic(raw(rows[0]))});assert.equal((await safe.call('get_live_bank_financials',{cert:14,quarter:'2026Q2 OR CERT:*'})).isError,true);
});
test('external source failures become tool errors, not fabricated observations',async()=>{
  const fail=createTools(async()=>dataset,{fetcher:async()=>new Response('down',{status:503})});assert.equal((await fail.call('get_live_bank_financials',{cert:14})).isError,true);
});
test('public snapshot loader checks the pinned hash before returning data',async()=>{
  const file=await readFile(new URL('./fixtures/financials.json',import.meta.url));
  const fetcher=async url=>url.endsWith('/financials.json')?new Response(file):Response.json(manifest);
  assert.equal((await loadPublicSnapshot(fetcher)).rows.length,4313);
  await assert.rejects(()=>loadPublicSnapshot(async url=>url.endsWith('/financials.json')?new Response(Buffer.concat([file,Buffer.from(' ')])):Response.json(manifest)),/checksum/);
});
test('every advertised tool has a title and truthful read-only annotations',()=>{
  assert.equal(TOOLS.length,8);for(const t of TOOLS){assert.ok(t.title);assert.equal(t.annotations.readOnlyHint,true);assert.equal(t.annotations.destructiveHint,false);assert.equal(t.inputSchema.additionalProperties,false);}
});
test('observability records only canonical tool names, status and elapsed time',async()=>{
  const events=[];const observed=createTools(async()=>dataset,{onToolResult:event=>events.push(event)});
  await observed.call('search',{query:'State Street'});await observed.call('unrecognized private text',{});
  assert.deepEqual(Object.keys(events[0]).sort(),['duration_ms','ok','tool']);assert.equal(events[0].tool,'search');assert.equal(events[1].tool,'unknown');assert.equal(events[1].ok,false);
});
test('HTTP validates origin, size, JSON, methods and protocol version',async()=>{
  assert.equal((await handler(request(rpc('tools/list'),{Origin:'https://evil.example'}))).status,403);
  assert.equal((await handler(new Request('https://www.banksonsale.com/api/mcp'))).status,405);
  assert.equal((await handler(request(rpc('tools/list'),{'MCP-Protocol-Version':'1900-01-01'}))).status,400);
  assert.equal((await handler(new Request('https://www.banksonsale.com/api/mcp',{method:'POST',body:' '.repeat(17000)}))).status,413);
  assert.equal((await handler(new Request('https://www.banksonsale.com/api/mcp',{method:'POST',body:'{'}))).status,400);
});
test('SDK initialization and Sites discovery both work',async()=>{
  const i=await handler(request(rpc('initialize',{protocolVersion:'2025-11-25',capabilities:{},clientInfo:{name:'test',version:'1'}})));assert.equal(i.status,200);assert.equal((await i.json()).result.serverInfo.name,'us-bank-data');
  const d=await (await handler(request(rpc('server/discover')))).json();assert.ok(d.result.supportedVersions.includes('2026-07-28'));
  const l=await (await handler(request(rpc('tools/list'),{'MCP-Protocol-Version':'2026-07-28'}))).json();assert.equal(l.result.tools.length,8);
  const c=await (await handler(request(rpc('tools/call',{name:'get_bank_financials',arguments:{cert:14}}),{'MCP-Protocol-Version':'2026-07-28'}))).json();assert.equal(c.result.structuredContent.cert,14);
});
test('official MCP client connects and calls tools over real Streamable HTTP',async()=>{
  const server=httpServer(async(req,res)=>{
    const r=new Request(`http://127.0.0.1:${server.address().port}`,{method:req.method,headers:req.headers,...(req.method==='POST'?{body:req,duplex:'half'}:{})});
    const response=await handler(r);res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const client=new Client({name:'us-bank-data-test',version:'1'},{capabilities:{}});
  try{
    await client.connect(new StreamableHTTPClientTransport(new URL(`http://127.0.0.1:${server.address().port}`)));
    assert.equal((await client.listTools()).tools.length,8);
    const r=await client.callTool({name:'get_bank_financials',arguments:{cert:14}});assert.equal(r.structuredContent.cert,14);
    assert.equal((await client.callTool({name:'get_bank_financials',arguments:{cert:0}})).isError,true);
  }finally{await client.close();await new Promise(resolve=>server.close(resolve));}
});
