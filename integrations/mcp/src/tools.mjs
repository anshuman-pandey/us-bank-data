import {CfWorkerJsonSchemaValidator} from '@modelcontextprotocol/sdk/validation/cfworker';
import {CLASSES, EDITION, METRICS, ORIGIN, RELEASE, REPORT_DATE, STATES} from './catalog.mjs';
import {datasetInfo,liveBank,snapshotDocument} from './data.mjs';

const object=(properties={},required=[])=>({type:'object',properties,required,additionalProperties:false});
const cert={type:'integer',minimum:1,maximum:999999,description:'FDIC institution certificate number; not a ticker or holding-company RSSD ID.'};
const certs={type:'array',items:cert,minItems:1,maxItems:10,uniqueItems:true};
const edition={type:'string',enum:[EDITION],description:'Frozen research edition. Omit to use the explicitly documented 2026-q2-r1 edition.'};
const annotation={readOnlyHint:true,destructiveHint:false,idempotentHint:true,openWorldHint:true};
const make=(name,title,description,inputSchema)=>({name,title,description,inputSchema,annotations:annotation,_meta:{securitySchemes:[{type:'noauth'}]}});

export const TOOLS=[
  make('search','Search US bank data','Search bank institution names, exact FDIC CERT identifiers, dataset coverage and metric definitions. Returns citable document IDs and URLs. Searches the frozen June 30, 2026 edition, not private accounts or credit unions.',object({query:{type:'string',minLength:1,maxLength:200}},['query'])),
  make('fetch','Read a US bank data source','Retrieve a complete source document returned by search. Accepts bank:CERT, metric:FDIC_FIELD or dataset:2026-q2-r1; no arbitrary URLs.',object({id:{type:'string',minLength:1,maxLength:80}},['id'])),
  make('get_dataset_info','Get bank dataset coverage and sources','Inspect the frozen US Bank Data edition, reporting and retrieval dates, 14 metrics, scope, licenses, downloads and live-data option. The frozen edition is not implicitly latest.',object()),
  make('get_bank_financials','Get frozen bank financials','Retrieve 14 financial measures for an exact FDIC CERT in frozen edition 2026-q2-r1 (June 30, 2026). Money is normalized to USD, ratios remain percent, missing stays null. Includes source and manifest links.',object({cert,edition},['cert'])),
  make('compare_banks','Compare banks at the same quarter','Compare 1–10 explicit FDIC CERT institutions in the same frozen June 30, 2026 edition. Returns each requested institution or an explicit missing record, units, reporting date and citations. No claim of a matched or representative peer group.',object({certs,edition},['certs'])),
  make('screen_banks','Screen a frozen bank cohort','Filter institution financial records by U.S. state/territory, bank class, current-at-retrieval active flag and USD asset bounds. Minimum inclusive, maximum exclusive. No implicit insured-only or active-only filter. Returns exact total and bounded, stable CERT pagination.',object({
    states:{type:'array',items:{type:'string',enum:[...STATES]},minItems:1,maxItems:10,uniqueItems:true},
    bank_classes:{type:'array',items:{type:'string',enum:CLASSES},minItems:1,maxItems:8,uniqueItems:true},
    active_in_source:{type:'boolean',description:'Explicit filter on source flag at retrieval, not historical active status.'},
    min_assets_usd:{type:'integer',minimum:0,maximum:Number.MAX_SAFE_INTEGER},max_assets_usd:{type:'integer',minimum:0,maximum:Number.MAX_SAFE_INTEGER},
    limit:{type:'integer',minimum:1,maximum:100},offset:{type:'integer',minimum:0,maximum:4313},edition,
  })),
  make('get_metric_definitions','Explain bank financial metrics','Get definitions, FDIC field names, normalized units, multipliers and limitations for 14 supported measures. Distinguishes CET1 from leverage, domestic from total deposits, and already annualized ROA/ROE.',object({fields:{type:'array',items:{type:'string',enum:METRICS.map(m=>m.field)},minItems:1,maxItems:14,uniqueItems:true}})),
  make('get_live_bank_financials','Get live FDIC bank financials','Query FDIC BankFind Suite now for an exact CERT. Omit quarter for that institution\'s most recent available observation, or supply YYYYQ1–YYYYQ4. Returns 14 fields normalized to USD/percent, the actual reporting date, retrieval time and the exact FDIC source URL. Live data may revise earlier quarters and differs from the frozen edition. Does not query credit unions or customer accounts.',object({cert,quarter:{type:'string',pattern:'^(19[89][0-9]|20[0-9]{2})Q[1-4]$'}},['cert'])),
];
const provider=new CfWorkerJsonSchemaValidator();
const validators=new Map(TOOLS.map(t=>[t.name,provider.getValidator(t.inputSchema)]));
const textResult=data=>({content:[{type:'text',text:JSON.stringify(data)}],structuredContent:data});
const normalized=s=>s.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const queryWords=new Set('a an and are as at bank banks by compare data deposits equity fdic financial financials find for from get give how i in is it latest loans me most of on please ratio ratios recent report reporting show size source sources s the their this to total us usd value values was were what which with assets capital cet1 leverage quarter income profitability return employees offices'.split(' '));

/**
 * @param {() => Promise<any>} getDataset
 * @param {{fetcher?: typeof fetch, onToolResult?: (event:{tool:string,ok:boolean,duration_ms:number})=>void}} options
 */
export function createTools(getDataset,{fetcher=fetch,onToolResult=undefined}={}) {
  async function execute(name,args={}) {
    const validate=validators.get(name);
    if(!validate) return {isError:true,content:[{type:'text',text:'Unknown tool.'}]};
    const check=validate(args);
    if(!check.valid) return {isError:true,content:[{type:'text',text:`Invalid arguments: ${check.errorMessage}`}]};
    try {
      if(name==='get_live_bank_financials')return textResult(await liveBank(args.cert,args.quarter,fetcher));
      if(name==='get_metric_definitions')return textResult({metrics:METRICS.filter(m=>!args.fields||args.fields.includes(m.field)),reporting_note:'Missing remains null; percent values are not fractions. USD monetary tool values have already been multiplied by 1000 from source fields.'});
      const dataset=await getDataset();
      const info=()=>datasetInfo(dataset);
      const bank=cert=>{const row=dataset.byCert.get(cert);return row?{found:true,...snapshotDocument(row,dataset)}:{found:false,cert,edition:EDITION,report_date:REPORT_DATE,reason:'No institution observation in this frozen edition; absence is not a zero balance.'};};
      if(name==='get_dataset_info')return textResult(info());
      if(name==='get_bank_financials')return textResult(bank(args.cert));
      if(name==='compare_banks')return textResult({edition:EDITION,report_date:REPORT_DATE,banks:args.certs.map(bank),peer_selection:'Explicit caller selection; not a matched or representative peer group.'});
      if(name==='screen_banks') {
        if(args.min_assets_usd!==undefined&&args.max_assets_usd!==undefined&&args.min_assets_usd>=args.max_assets_usd)throw new Error('Maximum assets must be greater than minimum assets.');
        const selected=dataset.rows.filter(r=>(!args.states||args.states.includes(r.state))&&(!args.bank_classes||args.bank_classes.includes(r.bank_class))&&(args.active_in_source===undefined||r.active_in_source===(args.active_in_source?1:0))&&(args.min_assets_usd===undefined||r.ASSET!==null&&r.ASSET*1000>=args.min_assets_usd)&&(args.max_assets_usd===undefined||r.ASSET!==null&&r.ASSET*1000<args.max_assets_usd)).sort((a,b)=>a.cert-b.cert);
        const offset=args.offset??0,limit=args.limit??25;
        return textResult({edition:EDITION,report_date:REPORT_DATE,total:selected.length,offset,limit,next_offset:offset+limit<selected.length?offset+limit:null,filters:args,banks:selected.slice(offset,offset+limit).map(r=>({cert:r.cert,name:r.name,state:r.state,city:r.city,bank_class:r.bank_class,active_in_source:r.active_in_source,assets_usd:r.ASSET===null?null:r.ASSET*1000,deposits_usd:r.DEP===null?null:r.DEP*1000,citation_url:`${ORIGIN}/banks/${r.cert}`})),source_manifest:`${RELEASE}/manifest.json`});
      }
      if(name==='search') {
        const q=normalized(args.query),tokens=q.split(' ');
        if(!q)throw new Error('Query must contain a letter or number.');
        const results=[];
        if(['bank data','us bank','u s bank','fdic','dataset','coverage','download','python','credit union','latest'].some(s=>q.includes(s)))results.push({id:`dataset:${EDITION}`,title:`US Bank Data — ${EDITION}: coverage, downloads and limitations`,url:RELEASE});
        for(const m of METRICS)if(tokens.every(t=>normalized(`${m.name} ${m.field} ${m.key}`).includes(t)))results.push({id:`metric:${m.field}`,title:`${m.name} — ${m.field} (${m.unit})`,url:m.definition_url});
        const exactCert=q.match(/^(?:fdic )?(?:cert(?:ificate)?(?: number)? )?([1-9]\d{0,5})$/)?.[1];
        const bankTerms=tokens.filter(t=>!queryWords.has(t)&&!/^20\d{2}(q[1-4])?$/.test(t));
        const matches=dataset.rows.map(r=>{
          const names=normalized(`${r.name} ${r.source_short_name}`),haystack=`${names} ${normalized(`${r.city} ${r.state}`)}`;
          const phrase=q.length>3&&names.includes(q);
          const matched=exactCert?Number(exactCert)===r.cert:phrase||bankTerms.length>0&&bankTerms.every(t=>haystack.split(' ').some(word=>word===t||word.startsWith(t)));
          return {r,matched,score:(phrase?100:0)+(names.startsWith(q)?50:0)};
        }).filter(x=>x.matched).sort((a,b)=>b.score-a.score||a.r.cert-b.r.cert).map(x=>x.r);
        for(const r of matches.slice(0,20))results.push({id:`bank:${r.cert}`,title:`${r.name} — CERT ${r.cert}, ${r.city}, ${r.state}; ${REPORT_DATE}`,url:`${ORIGIN}/banks/${r.cert}`});
        // Standard ChatGPT search/fetch shape: the content text is a JSON object
        // with a results array. Resolve ambiguous names instead of guessing a CERT.
        return textResult({results:results.slice(0,25)});
      }
      if(name==='fetch') {
        const [kind,key,...extra]=args.id.split(':');let doc,title,url;
        if(extra.length)throw new Error('Use an exact ID returned by search.');
        if(kind==='dataset'&&key===EDITION){doc=info();title=`US Bank Data ${EDITION}`;url=RELEASE;}
        else if(kind==='metric'&&METRICS.some(m=>m.field===key)){doc=METRICS.find(m=>m.field===key);title=doc.name;url=doc.definition_url;}
        else if(kind==='bank'&&/^[1-9]\d{0,5}$/.test(key)&&dataset.byCert.has(Number(key))){doc=bank(Number(key));title=doc.name;url=doc.provenance.citation_url;}
        else throw new Error('Document not found. Use an ID returned by search; arbitrary URLs are not fetched.');
        return textResult({id:args.id,title,text:JSON.stringify(doc),url,metadata:{edition:EDITION,report_date:REPORT_DATE}});
      }
      throw new Error('Tool is unavailable.');
    } catch(error) {
      // Errors contain controlled source/validation messages, never credentials,
      // HTTP bodies, request headers or private account data.
      return {isError:true,content:[{type:'text',text:error instanceof Error?error.message:'Data source temporarily unavailable.'}]};
    }
  }
  async function call(name,args={}) {
    const start=performance.now(),response=await execute(name,args);
    if(typeof onToolResult==='function')onToolResult({tool:validators.has(name)?name:'unknown',ok:!response.isError,duration_ms:Math.round(performance.now()-start)});
    return response;
  }
  return {list:()=>TOOLS,call};
}
