"""BanksOnSale's data contract, integrity checks, and portable exports."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from importlib.resources import files
from pathlib import Path
from typing import Any

BRAND = "BanksOnSale"
HOME = "https://banksonsale.com"
SCHEMA_VERSION = "1.0"
PACKAGE_VERSION = "0.1.0"


class DataError(RuntimeError):
    """A source response or saved dataset does not meet the data contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def checksum(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def metric_definitions() -> dict[str, dict[str, Any]]:
    """Return independent copies of the audited BanksOnSale metric definitions."""
    catalog = json.loads(files("banksonsale_data").joinpath("resources/metrics.json").read_text())
    return {item["name"]: item for item in catalog["metrics"]}


def normalize_number(value: Any, multiplier: int = 1) -> int | float | None:
    """Keep reported zero and negative numbers; normalize explicit absence only."""
    if value is None or (isinstance(value, str) and value.strip().upper() in {
        "", "NA", "N/A", "NULL", "NONE", "NAN",
    }):
        return None
    if isinstance(value, bool):
        raise DataError("A boolean is not a reported numeric metric.")
    try:
        number = Decimal(str(value).strip()) * multiplier
    except (InvalidOperation, ValueError) as exc:
        raise DataError(f"Invalid numeric source value: {value!r}") from exc
    if not number.is_finite():
        raise DataError("A reported metric must be finite or explicitly absent.")
    return int(number) if number == number.to_integral_value() else float(number)


@dataclass
class BankPanel:
    """One bank, an explicit calendar-quarter window, and its original evidence."""

    document: dict[str, Any]

    @classmethod
    def create(cls, *, bank: dict[str, Any], rows: list[dict[str, Any]],
               sources: list[dict[str, Any]], requested_dates: list[str],
               report_date_defaulted: bool) -> BankPanel:
        definitions = metric_definitions()
        content = {
            "publisher": BRAND,
            "publisher_url": HOME,
            "package_version": PACKAGE_VERSION,
            "schema_version": SCHEMA_VERSION,
            "bank": bank,
            "requested_dates": requested_dates,
            "report_date_defaulted": report_date_defaulted,
            "metric_definitions": definitions,
            "rows": rows,
            "sources": sources,
            "coverage": {
                "requested_quarters": len(requested_dates),
                "reported_quarters": sum(row["report_available"] for row in rows),
                "missing_quarters": [row["report_date"] for row in rows if not row["report_available"]],
                "metric_missing_counts": {
                    key: sum(row[key] is None for row in rows) for key in definitions
                },
            },
            "limitations": [
                "FDIC BankFind institution records; not consolidated holding-company financials.",
                "Current upstream revisions and institution identity labels at retrieval; not historical information-as-known-at-the-time.",
                "Reported zeros are preserved; applicability of a zero is not inferred.",
                "The requested calendar quarters are never filled with older reports or estimates.",
            ],
        }
        digest = checksum(content)
        document = dict(content, content_sha256=digest,
                        dataset_id=f"banksonsale-fdic-{bank['cert']}-{requested_dates[-1]}-{digest[:12]}")
        panel = cls(document)
        panel.validate()
        return panel

    def validate(self) -> None:
        """Check a saved snapshot's integrity and its basic contract."""
        doc = self.document
        if doc.get("schema_version") != SCHEMA_VERSION or doc.get("publisher") != BRAND:
            raise DataError("Unsupported BanksOnSale dataset schema or publisher.")
        content = {key: value for key, value in doc.items() if key not in {"content_sha256", "dataset_id"}}
        if checksum(content) != doc.get("content_sha256"):
            raise DataError("BanksOnSale snapshot checksum does not match its contents.")
        for source in doc.get("sources", []):
            if hashlib.sha256(source["raw_json"].encode("utf-8")).hexdigest() != source["sha256"]:
                raise DataError("An archived FDIC response checksum does not match.")
        dates = doc.get("requested_dates", [])
        if not dates or [row["report_date"] for row in doc.get("rows", [])] != dates:
            raise DataError("Rows must match the requested calendar-quarter window.")
        if len(set(dates)) != len(dates) or dates != sorted(dates):
            raise DataError("Quarter dates must be unique and ascending.")
        if any(row["cert"] != doc["bank"]["cert"] for row in doc["rows"]):
            raise DataError("The snapshot contains a different bank entity.")
        expected_id = f"banksonsale-fdic-{doc['bank']['cert']}-{dates[-1]}-{doc['content_sha256'][:12]}"
        if doc.get("dataset_id") != expected_id:
            raise DataError("BanksOnSale dataset identity does not match its contents.")

    @property
    def rows(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.document["rows"])

    @property
    def dataset_id(self) -> str:
        return self.document["dataset_id"]

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self.document)

    def manifest(self) -> dict[str, Any]:
        """Evidence, definitions, branding, and coverage without the numeric panel."""
        return copy.deepcopy({key: value for key, value in self.document.items() if key != "rows"})

    def to_pandas(self):
        """Return a DataFrame with BanksOnSale provenance in its attrs."""
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError("Install banksonsale-data[pandas] to use to_pandas().") from exc
        frame = pd.DataFrame(self.rows)
        frame.attrs["banksonsale"] = self.manifest()
        return frame

    def to_polars(self):
        """Return a Polars DataFrame; retain evidence using manifest() or export()."""
        try:
            import polars as pl
        except ImportError as exc:
            raise ImportError("Install banksonsale-data[polars] to use to_polars().") from exc
        return pl.DataFrame(self.rows)

    def export(self, path: str | Path) -> Path:
        """Write a JSON snapshot, CSV plus evidence, or source-linked Parquet."""
        self.validate()
        target = Path(path)
        extension = target.suffix.lower()
        if extension not in {".json", ".csv", ".parquet"}:
            raise ValueError("Use a .json, .csv, or .parquet output filename.")
        target.parent.mkdir(parents=True, exist_ok=True)
        if extension == ".json":
            target.write_text(json.dumps(self.document, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        elif extension == ".csv":
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=list(self.document["rows"][0]))
            writer.writeheader()
            writer.writerows(self.rows)
            raw = buffer.getvalue().encode("utf-8")
            target.write_bytes(raw)
            manifest = dict(self.manifest(), artifact_sha256=hashlib.sha256(raw).hexdigest(),
                            artifact_filename=target.name)
            target.with_suffix(".manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        else:
            try:
                import pyarrow as pa
                import pyarrow.parquet as pq
            except ImportError as exc:
                raise ImportError("Install banksonsale-data[parquet] to export Parquet.") from exc
            table = pa.Table.from_pylist(self.rows)
            table = table.replace_schema_metadata({b"banksonsale": canonical_json(self.manifest()).encode("utf-8")})
            pq.write_table(table, target)
        return target

    @classmethod
    def load(cls, path: str | Path) -> BankPanel:
        """Reload and verify a self-contained BanksOnSale JSON snapshot."""
        panel = cls(json.loads(Path(path).read_text(encoding="utf-8")))
        panel.validate()
        return panel
