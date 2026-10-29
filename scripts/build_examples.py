"""Generate the release's notebooks and small source-linked comparison from pinned samples."""
import csv
import hashlib
import io
import json
from pathlib import Path

from banksonsale_data import load_sample

ROOT = Path(__file__).resolve().parents[1]
panels = [load_sample(cert) for cert in (628, 3510, 58665)]
columns = ['cert', 'bank_name', 'report_date', 'assets_usd', 'deposits_usd', 'cet1_ratio_pct', 'leverage_ratio_pct', 'roa_pct']
rows = [{key: panel.rows[-1][key] for key in columns} for panel in panels]
assert {row['report_date'] for row in rows} == {'2026-06-30'}
stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, fieldnames=columns)
writer.writeheader(); writer.writerows(rows)
raw = stream.getvalue().encode('utf-8')
(ROOT/'examples/comparison-2026-q2.csv').write_bytes(raw)
(ROOT/'examples/comparison-2026-q2.manifest.json').write_text(json.dumps({
    'publisher': 'BanksOnSale', 'purpose': 'Same-quarter interface example across different bank sizes; not a matched peer group, ranking or recommendation.',
    'report_date': '2026-06-30', 'artifact_sha256': hashlib.sha256(raw).hexdigest(),
    'panels': [panel.manifest() for panel in panels],
}, indent=2)+'\n')

def md(text): return {'cell_type':'markdown','metadata':{},'source':text.splitlines(keepends=True)}
def code(text): return {'cell_type':'code','metadata':{},'source':text.splitlines(keepends=True),'execution_count':None,'outputs':[]}
install = '''import importlib.util
import subprocess
import sys

if importlib.util.find_spec("usbankdata") is None:
    subprocess.check_call([sys.executable, "-m", "pip", "install",
        "https://github.com/anshuman-pandey/us-bank-data/releases/download/v0.1.1/us_bank_data-0.1.1-py3-none-any.whl"])
'''
first = [
 md('# US Bank Data: one bank, eight quarters\n\nA reproducible financial panel for a class, notebook or application. Original source: FDIC BankFind Suite. This example uses a **frozen 2026Q2 sample**, not a latest-data claim. After installing the package, no source network requests are needed. Use a fresh Python 3.10+ notebook environment.\n'),
 code(install),
 code('from usbankdata import load_sample\n\npanel = load_sample(58665)\nprint(panel.document["bank"]["name"])\nprint(panel.document["requested_dates"])\nprint(panel.document["coverage"])\n'),
 md('## Inspect explicit units\n\nMoney is USD. Ratios are percent: 12.5 means 12.5%. Missing stays `None`; zero stays zero. CET1 uses RBCT1CER; leverage uses RBC1AAJ. The bank is distinct from its listed parent.\n'),
 code('latest = panel.rows[-1]\nfor field in ["report_date", "assets_usd", "deposits_usd", "cet1_ratio_pct", "leverage_ratio_pct", "roa_pct"]:\n    print(field, latest[field])\nprint(panel.document["metric_definitions"]["assets_usd"])\nassert latest["report_date"] == "2026-06-30"\n'),
 md('## Keep the evidence with the export\n\nThe CSV sidecar records the source URLs, retrieval times, raw source responses, metric definitions and file hash. The JSON snapshot can be loaded and checked later. Hashes detect content changes, not whether the original filing is economically correct.\n'),
 code('from pathlib import Path\nfrom usbankdata import BankPanel\n\noutput = Path("outputs/banksonsale-example")\npanel.export(output / "live-oak.csv")\npanel.export(output / "live-oak.json")\nrestored = BankPanel.load(output / "live-oak.json")\nassert restored.rows == panel.rows\nprint(panel.dataset_id)\nprint(output / "live-oak.manifest.json")\n'),
 md('## Optional live request\n\nUse `bank(58665).financials(quarters=8, through="2026Q2")` to fetch a new source snapshot for an explicit period. Omitting `through` selects that bank\'s latest available report date, which can differ from another bank\'s latest date.\n\nFor hosted saved research and monitoring, [continue in BanksOnSale](https://www.banksonsale.com/banks/58665). Hosted data editions are displayed separately; coverage can differ. The open package works without registering. Cite **BanksOnSale Data, sourced from FDIC BankFind Suite**, with the report dates and dataset ID.\n'),
]
second = [
 md('# US Bank Data: compare an exact quarter\n\nUse three real, pinned sample institutions to demonstrate a same-quarter comparison and SQL. They have very different sizes and business models: **this is not a matched peer group, ranking or investment recommendation**. Frozen report date: **2026-06-30**.\n'),
 code(install),
 code('from usbankdata import load_sample\n\npanels = [load_sample(cert) for cert in (628, 3510, 58665)]\nrows = [panel.rows[-1] for panel in panels]\nassert {row["report_date"] for row in rows} == {"2026-06-30"}\nfor row in rows:\n    print(row["cert"], row["bank_name"], row["report_date"], row["assets_usd"])\n'),
 md('## Query the table using standard-library SQL\n\nUse an explicit CERT, not a ticker or similarly named parent. Leave missing ratios as SQL NULL. Zero and negative observations remain valid.\n'),
 code('import sqlite3\n\nconnection = sqlite3.connect(":memory:")\nconnection.execute("CREATE TABLE banks (cert INTEGER, bank_name TEXT, report_date TEXT, assets_usd INTEGER, deposits_usd INTEGER, cet1_ratio_pct REAL, leverage_ratio_pct REAL, roa_pct REAL)")\ncolumns = ["cert", "bank_name", "report_date", "assets_usd", "deposits_usd", "cet1_ratio_pct", "leverage_ratio_pct", "roa_pct"]\nconnection.executemany("INSERT INTO banks VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [[row[column] for column in columns] for row in rows])\nfor result in connection.execute("SELECT bank_name, report_date, assets_usd, cet1_ratio_pct, leverage_ratio_pct FROM banks ORDER BY cert"):\n    print(result)\nconnection.close()\n'),
 md('## Export a comparison and a source recipe\n\nA CSV is easy to share, but cannot carry all evidence by itself. Keep its manifest and the constituent dataset IDs. Do not infer that an institution is available for sale.\n'),
 code('import csv\nimport hashlib\nimport json\nfrom pathlib import Path\n\noutput = Path("outputs/banksonsale-comparison")\noutput.mkdir(parents=True, exist_ok=True)\npath = output / "comparison.csv"\nwith path.open("w", newline="", encoding="utf-8") as file:\n    writer = csv.DictWriter(file, fieldnames=columns)\n    writer.writeheader()\n    writer.writerows([{key: row[key] for key in columns} for row in rows])\nrecipe = {"publisher": "BanksOnSale", "report_date": "2026-06-30", "certs": [row["cert"] for row in rows], "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "panels": [panel.manifest() for panel in panels]}\n(output / "comparison.manifest.json").write_text(json.dumps(recipe, indent=2), encoding="utf-8")\nassert len(rows) == 3\nprint(path)\n'),
 md('## Continue your own research\n\nChoose peers based on size, charter and business model for the question you are answering. For an existing analysis environment, these same records work with pandas, Polars or DuckDB. For hosted screening and saved research, [explore BanksOnSale](https://www.banksonsale.com/discover). Professional features can require a subscription and display their own data edition.\n\nOriginal source: FDIC BankFind Suite. Publisher: **BanksOnSale Data**. [Methods and units](https://www.banksonsale.com/methodology).\n'),
]
for name,cells in [('01_bank_financials',first),('02_compare_banks',second)]:
 notebook={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12.0'}},'cells':cells}
 for number,cell in enumerate(cells): cell['id']=f'banksonsale-{number:02d}'
 (ROOT/'notebooks'/f'{name}.ipynb').write_text(json.dumps(notebook,indent=1)+'\n')
