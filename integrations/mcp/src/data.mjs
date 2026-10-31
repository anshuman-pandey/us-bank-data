import {CAVEATS, EDITION, METRICS, ORIGIN, RELEASE, REPORT_DATE, REPOSITORY, SNAPSHOT_SHA256} from './catalog.mjs';

export function validateSnapshot(rows, manifest) {
  if (!Array.isArray(rows) || rows.length !== 4313 || manifest.release !== EDITION || manifest.report_date !== REPORT_DATE || manifest.record_count !== rows.length) throw new Error('Snapshot edition or population mismatch');
  const certs = new Set();
  for (const row of rows) {
    if (!Number.isInteger(row.cert) || row.cert < 1 || certs.has(row.cert) || row.report_date !== REPORT_DATE || typeof row.name !== 'string') throw new Error('Invalid or duplicate snapshot institution');
    certs.add(row.cert);
    for (const {field} of METRICS) if (!(field in row) || (row[field] !== null && (typeof row[field] !== 'number' || !Number.isFinite(row[field])))) throw new Error(`Invalid snapshot metric: ${field}`);
  }
  return {rows,manifest,byCert:new Map(rows.map(row=>[row.cert,row]))};
}

export function datasetInfo(dataset) {
  return {
    name:'US Bank Data',edition:EDITION,report_date:REPORT_DATE,record_count:dataset.rows.length,
    retrieved_at:dataset.manifest.retrieved_at,mode:'frozen',is_latest:false,
    live_access:'get_live_bank_financials queries FDIC at request time; omit quarter for that institution\'s most recent available observation. No automatic frozen-edition refresh is claimed.',
    monetary_unit:'USD in MCP financial results; website raw files use USD thousands',ratio_unit:'percent',
    metrics:METRICS,scope:dataset.manifest.scope,bank_class_counts:dataset.manifest.bank_class_counts,
    limitations:CAVEATS,
    sources:[{title:`US Bank Data frozen edition ${EDITION}`,url:RELEASE},{title:'FDIC BankFind Suite',url:'https://api.fdic.gov/banks/docs/'}],
    downloads:{json:`${RELEASE}/financials.json`,csv:`${RELEASE}/financials.csv`,manifest:`${RELEASE}/manifest.json`,json_sha256:SNAPSHOT_SHA256},
    python:{install:'pip install us-bank-data==0.2.0',import:'usbankdata',repository:REPOSITORY},
    license:'BanksOnSale compilation and original metadata: CC BY 4.0; code: MIT. FDIC is the original source. No FDIC endorsement.',
    documentation:`${ORIGIN}/ai`,
  };
}

export function bankDocument(row, provenance) {
  const values = Object.fromEntries(METRICS.map(m=>[m.key,row[m.field]===null?null:row[m.field]*m.multiplier]));
  return {
    cert:row.cert,rssd_id:row.rssd_id,name:row.name,city:row.city,state:row.state,bank_class:row.bank_class,
    active_in_source:row.active_in_source,report_date:row.report_date,values,
    units:Object.fromEntries(METRICS.map(m=>[m.key,m.unit])),missing_fields:METRICS.filter(m=>row[m.field]===null).map(m=>m.key),
    provenance,
  };
}

export function snapshotDocument(row,dataset) {
  return bankDocument(row,{
    mode:'frozen',edition:EDITION,retrieved_at:dataset.manifest.retrieved_at,
    citation_url:`${ORIGIN}/banks/${row.cert}`,release_url:RELEASE,
    source_url:fdicFinancialsUrl(row.cert,`${row.report_date.slice(0,4)}Q${Number(row.report_date.slice(5,7))/3}`),
    manifest_url:`${RELEASE}/manifest.json`,json_sha256:SNAPSHOT_SHA256,
    attribution:'US Bank Data; BanksOnSale compilation and metadata, sourced from FDIC BankFind Suite.',
  });
}

export function fdicFinancialsUrl(cert,quarter) {
  let filters=`CERT:${cert}`;
  if (quarter) { const y=quarter.slice(0,4), q=Number(quarter.at(-1)); filters+=` AND REPDTE:${y}${['0331','0630','0930','1231'][q-1]}`; }
  const params=new URLSearchParams({filters,fields:['CERT','RSSDID','NAME','NAMEFULL','CITY','STALP','BKCLASS','ACTIVE','REPDTE',...METRICS.map(m=>m.field)].join(','),sort_by:'REPDTE',sort_order:'DESC',limit:'1',format:'json'});
  return `https://api.fdic.gov/banks/financials?${params}`;
}

async function boundedJson(response,maxBytes) {
  if (!response.ok) throw new Error(`Public data source returned HTTP ${response.status}`);
  const reader=response.body.getReader();let length=0;const chunks=[];
  try {for (;;) {const {done,value}=await reader.read();if(done)break;length+=value.length;if(length>maxBytes)throw new Error('Public data response exceeded size limit');chunks.push(value);}}
  finally {await reader.cancel().catch(()=>{});}
  const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
  return {data:JSON.parse(new TextDecoder().decode(bytes)),bytes};
}

export async function loadPublicSnapshot(fetcher=fetch) {
  const request=url=>fetcher(url,{headers:{'User-Agent':'USBankDataMCP/0.1 (+https://www.banksonsale.com/ai)'},signal:AbortSignal.timeout(15000)});
  const [raw,meta]=await Promise.all([request(`${RELEASE}/financials.json`).then(r=>boundedJson(r,2500000)),request(`${RELEASE}/manifest.json`).then(r=>boundedJson(r,100000))]);
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw.bytes))).map(n=>n.toString(16).padStart(2,'0')).join('');
  if(digest!==SNAPSHOT_SHA256)throw new Error('Snapshot checksum mismatch');
  return validateSnapshot(raw.data,meta.data);
}

export async function liveBank(cert,quarter,fetcher=fetch) {
  const url=fdicFinancialsUrl(cert,quarter);
  const {data:payload}=await boundedJson(await fetcher(url,{headers:{'User-Agent':'USBankDataMCP/0.1 (+https://www.banksonsale.com/ai)'},signal:AbortSignal.timeout(12000)}),100000);
  const total=Number(payload.totals?.count);
  if (!Number.isInteger(total)||total<0||!Array.isArray(payload.data)) throw new Error('Unexpected FDIC response envelope');
  if(total===0) {if(payload.data.length)throw new Error('Inconsistent FDIC empty result');return {found:false,cert,quarter:quarter??null,source_url:url,reason:'No observation returned by FDIC; absence is not a zero balance.'};}
  if(payload.data.length!==1)throw new Error('Unexpected FDIC result count');
  const d=payload.data[0]?.data;
  if(!d||Number(d.CERT)!==cert||!/^(19|20)\d{2}(0331|0630|0930|1231)$/.test(String(d.REPDTE)))throw new Error('FDIC institution or reporting date mismatch');
  const date=String(d.REPDTE);
  if(quarter&&date!==`${quarter.slice(0,4)}${['0331','0630','0930','1231'][Number(quarter.at(-1))-1]}`)throw new Error('FDIC returned the wrong quarter');
  const row={cert,rssd_id:d.RSSDID??null,name:d.NAMEFULL||d.NAME,city:d.CITY??null,state:d.STALP??null,bank_class:d.BKCLASS??null,active_in_source:d.ACTIVE??null,report_date:`${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}`};
  if(typeof row.name!=='string'||!row.name)throw new Error('FDIC institution name missing');
  for(const {field} of METRICS){if(!(field in d)||!(d[field]===null||typeof d[field]==='number'&&Number.isFinite(d[field])))throw new Error(`FDIC metric missing or invalid: ${field}`);row[field]=d[field];}
  return {found:true,...bankDocument(row,{mode:'live',edition:null,retrieved_at:new Date().toISOString(),source_url:url,citation_url:url,source_index:payload.meta?.index??null,attribution:'FDIC BankFind Suite, retrieved through US Bank Data by BanksOnSale.',limitation:'Latest available for this CERT if quarter is omitted, not a guarantee that every institution has filed the latest calendar quarter. Live observations can be revised; this is not the frozen edition.'})};
}
