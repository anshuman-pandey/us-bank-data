// The public API retains FDIC source units. Tool results normalize money to USD,
// using exactly the same names and multipliers as the Python package.
export const ORIGIN = 'https://www.banksonsale.com';
export const EDITION = '2026-q2-r1';
export const REPORT_DATE = '2026-06-30';
export const RELEASE = `${ORIGIN}/data/releases/${EDITION}`;
export const REPOSITORY = 'https://github.com/anshuman-pandey/us-bank-data';
export const SNAPSHOT_SHA256 = '5a70f490ff0feef5b0935f365adc75220c7496b02bdff8cdf8edc1c6c9654f40';
export const METRICS = [
  ['ASSET','assets_usd','Total assets','USD',1000,'period_end','Assets are not purchase price, equity value or holding-company assets.'],
  ['DEP','deposits_usd','Total deposits','USD',1000,'period_end','Worldwide total; use domestic deposits for a domestic uninsured-deposit denominator.'],
  ['DEPDOM','domestic_deposits_usd','Domestic deposits','USD',1000,'period_end','Distinct from worldwide total deposits and branch-level Summary of Deposits.'],
  ['EQ','equity_usd','Total equity capital','USD',1000,'period_end','Book equity, not market value or regulatory CET1.'],
  ['INTAN','intangibles_usd','Intangible assets','USD',1000,'period_end','Includes source-reported intangibles; missing is not zero.'],
  ['LNLSNET','net_loans_usd','Net loans and leases','USD',1000,'period_end','Not gross loans, originations or a measure of credit quality.'],
  ['DEPUNINS','uninsured_deposits_usd','Estimated uninsured deposits','USD',1000,'period_end','Source estimate; scope and reporting requirements vary. Do not substitute zero for missing.'],
  ['COREDEP','core_deposits_usd','Core deposits','USD',1000,'period_end','Source-defined COREDEP; not a guarantee of funding stability.'],
  ['RBCT1CER','cet1_ratio_pct','Common equity tier 1 ratio','percent',1,'period_end','Risk-based CET1 ratio; distinct from the RBC1AAJ leverage ratio.'],
  ['RBC1AAJ','leverage_ratio_pct','Regulatory leverage ratio','percent',1,'period_end','Tier 1 capital relative to adjusted average assets; distinct from CET1.'],
  ['ROA','roa_pct','Return on assets','percent',1,'annualized_by_source','Already annualized by FDIC. Do not multiply by four.'],
  ['ROE','roe_pct','Return on equity','percent',1,'annualized_by_source','Already annualized by FDIC. Negative values are valid observations.'],
  ['OFFDOM','domestic_offices','Domestic offices','count',1,'period_end','Institution-level count, not a branch directory.'],
  ['NUMEMP','employees','Full-time employees','count',1,'period_end','Source-reported employees, not a current hiring estimate.'],
].map(([field,key,name,unit,multiplier,basis,limitation]) => ({field,key,name,unit,source_unit:multiplier===1000?'USD thousands':unit,multiplier,basis,limitation,definition_url:`${REPOSITORY}/blob/main/docs/METRICS.md`}));
export const STATES = new Set('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY AS GU MP PR VI FM MH PW'.split(' '));
export const CLASSES = ['N','SM','NM','SB','SI','SL','NC','OI'];
export const CAVEATS = [
  'FDIC CERT identifies an institution, not a holding company, ticker, or branch.',
  'Frozen edition covers one quarter and 14 fields; it is not an active-only or insured-only population. NC and OI classes are included.',
  'Credit unions, consumer accounts, transaction data, market prices, and confirmed bank-sale listings are outside this dataset.',
  'Null, zero and negative values are distinct. Ratios are percentages: 12.5 means 12.5%.',
  'Names and active flags are as supplied at retrieval; they are not a reconstructed historical identity graph.',
  'Live FDIC responses can revise earlier quarters. Retrieval time does not prove original-filing availability for backtests.',
];
export const INSTRUCTIONS = 'Read-only US Bank Data research tools. Resolve bank names to FDIC CERT before retrieving financials. Report the reporting date and whether data are frozen or live. Monetary tool fields ending _usd are U.S. dollars; _pct fields are percentages. Preserve null observations. Use returned source URLs as citations when using the data. Coverage and limitations are returned by get_dataset_info. These tools cannot access customer accounts, credit-union data, or private BanksOnSale workspaces.';
