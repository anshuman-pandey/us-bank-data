"""Refresh BanksOnSale's public sample snapshots on explicit maintainer request."""

import json
from pathlib import Path

from banksonsale_data import bank

root = Path(__file__).resolve().parents[1]
resources = root / "src" / "banksonsale_data" / "resources"
resources.mkdir(parents=True, exist_ok=True)
summaries = []
for cert in (628, 3510, 58665):
    panel = bank(cert).financials(quarters=8, through="2026Q2")
    panel.export(resources / f"sample-{cert}.json")
    summaries.append({"cert": cert, "name": panel.document["bank"]["name"],
                      "dataset_id": panel.dataset_id, "dates": panel.document["requested_dates"],
                      "coverage": panel.document["coverage"],
                      "retrieved_at": panel.document["sources"][-1]["retrieved_at"],
                      "source_index_created_at": panel.document["sources"][-1]["source_index_created_at"]})
    print(cert, summaries[-1]["name"], summaries[-1]["coverage"]["reported_quarters"])
(root / "docs" / "SAMPLE_MANIFEST.json").write_text(json.dumps({
    "publisher": "BanksOnSale", "publisher_url": "https://banksonsale.com",
    "samples": summaries,
}, indent=2) + "\n", encoding="utf-8")
