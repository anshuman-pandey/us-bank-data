"""Explicit bank cohorts with portable source evidence and aligned quarter rows."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from banksonsale_data import DataError, FDICClient, load_sample, metric_definitions
from banksonsale_data.client import (
    INSTITUTION_FIELDS,
    quarter_end,
    quarter_window,
    source_date,
    validate_cert,
)
from banksonsale_data.models import canonical_json, checksum, normalize_number

VERSION = "0.2.0"
SCHEMA = "usbankdata.cohort.v1"
MAX_BANKS = 100
LIMITATIONS = [
    "Selected FDIC institution financials, not consolidated holding-company financials or a for-sale list.",
    "Identity labels are as retrieved, not a reconstructed historical identity graph.",
    "Report dates differ from retrieval dates; retained editions are not original-filing vintages.",
    "Missing filings and missing fields remain distinct; zeros and negative reported values are preserved.",
]


def _certs(values: Sequence[int], *, maximum: int | None = MAX_BANKS) -> list[int]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
        raise ValueError("certs must be a nonempty sequence of explicit FDIC certificate integers.")
    result = [validate_cert(value) for value in values]
    if len(set(result)) != len(result):
        raise ValueError("certs must not contain duplicates.")
    if maximum is not None and len(result) > maximum:
        raise ValueError(f"Select at most {maximum} banks per live cohort request.")
    return sorted(result)


def _coverage(rows: list[dict], banks: list[dict], dates: list[str]) -> dict:
    fields = metric_definitions()
    return {
        "banks": len(banks),
        "quarters": len(dates),
        "requested_bank_quarters": len(banks) * len(dates),
        "reported_bank_quarters": sum(row["report_available"] for row in rows),
        "missing_bank_quarters": [
            {"cert": row["cert"], "report_date": row["report_date"]}
            for row in rows
            if not row["report_available"]
        ],
        "fields": {
            key: {
                "reported": sum(row[key] is not None for row in rows),
                "missing": sum(row[key] is None for row in rows),
                "zero": sum(row[key] == 0 for row in rows),
            }
            for key in fields
        },
    }


@dataclass
class BankCohort:
    """A declared set of bank entities and dates, including explicit missing filings."""

    document: dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        banks: list[dict],
        rows: list[dict],
        dates: list[str],
        sources: list[dict],
        selection: dict,
        edition: dict | None = None,
    ) -> BankCohort:
        content = copy.deepcopy(
            {
                "schema_version": SCHEMA,
                "package_version": VERSION,
                "publisher": "US Bank Data",
                "banks": sorted(banks, key=lambda item: item["cert"]),
                "requested_dates": dates,
                "rows": sorted(rows, key=lambda item: (item["cert"], item["report_date"])),
                "metric_definitions": metric_definitions(),
                "selection": selection,
                "sources": sources,
                "edition": edition,
                "coverage": _coverage(rows, banks, dates),
                "limitations": LIMITATIONS,
            }
        )
        digest = checksum(content)
        obj = cls(
            dict(content, content_sha256=digest, dataset_id=f"usbankdata-cohort-{digest[:16]}")
        )
        obj.validate()
        return obj

    def validate(self) -> None:
        """Validate content, source archives, quarter keys, definitions and coverage."""
        try:
            doc = self.document
            if doc["schema_version"] != SCHEMA or doc["publisher"] != "US Bank Data":
                raise DataError("Unsupported US Bank Data cohort schema.")
            content = {
                key: value
                for key, value in doc.items()
                if key not in {"content_sha256", "dataset_id"}
            }
            if checksum(content) != doc["content_sha256"]:
                raise DataError("Cohort content checksum does not match.")
            if doc["dataset_id"] != f"usbankdata-cohort-{doc['content_sha256'][:16]}":
                raise DataError("Cohort identity does not match its contents.")
            definitions = metric_definitions()
            if doc["metric_definitions"] != definitions:
                raise DataError("Cohort metric definitions do not match this supported schema.")
            dates = doc["requested_dates"]
            if (
                not dates
                or len(dates) > 40
                or dates != quarter_window(quarter_end(dates[-1]), len(dates))
            ):
                raise DataError("Cohort dates must be a contiguous ascending quarter window.")
            certs = [validate_cert(bank["cert"]) for bank in doc["banks"]]
            if certs != sorted(set(certs)):
                raise DataError("Cohort banks must be unique and sorted.")
            expected = [(cert, date) for cert in certs for date in dates]
            if [(row["cert"], row["report_date"]) for row in doc["rows"]] != expected:
                raise DataError(
                    "Cohort rows must match every selected bank and requested quarter exactly once."
                )
            names = {bank["cert"]: bank["name"] for bank in doc["banks"]}
            for row in doc["rows"]:
                if type(row["cert"]) is not int or row["bank_name"] != names[row["cert"]]:
                    raise DataError(
                        "A cohort row has an invalid bank identity label or identifier."
                    )
                if type(row["report_available"]) is not bool:
                    raise DataError("report_available must be a boolean.")
                for field in definitions:
                    value = row[field]
                    if value is not None and (
                        type(value) not in (int, float) or normalize_number(value) != value
                    ):
                        raise DataError(f"Invalid normalized metric: {field}.")
                    if not row["report_available"] and value is not None:
                        raise DataError("An absent filing cannot contain reported metrics.")
            for source in doc["sources"]:
                if (
                    hashlib.sha256(source["raw_json"].encode("utf-8")).hexdigest()
                    != source["sha256"]
                ):
                    raise DataError("An archived source response checksum does not match.")
                json.loads(source["raw_json"])
            if doc["coverage"] != _coverage(doc["rows"], doc["banks"], dates):
                raise DataError("Cohort coverage does not match its observations.")
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
            raise DataError("Malformed US Bank Data cohort document.") from exc

    @property
    def rows(self) -> list[dict]:
        return copy.deepcopy(self.document["rows"])

    @property
    def banks(self) -> list[dict]:
        return copy.deepcopy(self.document["banks"])

    @property
    def certs(self) -> list[int]:
        return [bank["cert"] for bank in self.document["banks"]]

    @property
    def dataset_id(self) -> str:
        return self.document["dataset_id"]

    def to_dict(self) -> dict:
        return copy.deepcopy(self.document)

    def manifest(self) -> dict:
        return copy.deepcopy({key: value for key, value in self.document.items() if key != "rows"})

    def select(
        self,
        *,
        certs: Sequence[int] | None = None,
        states: Sequence[str] | None = None,
        bank_classes: Sequence[str] | None = None,
        min_assets_usd: int | None = None,
        max_assets_usd: int | None = None,
    ) -> BankCohort:
        """Filter a single-quarter snapshot; the selection anchor remains explicit.

        The minimum asset bound is inclusive and maximum exclusive. No active-bank
        filter is applied implicitly. Empty results are legitimate zero-row cohorts.
        """
        self.validate()
        if len(self.document["requested_dates"]) != 1:
            raise ValueError(
                "Select a cohort on a single-quarter snapshot before requesting its history."
            )
        requested = _certs(certs, maximum=None) if certs is not None else None
        if requested is not None and set(requested) - set(self.certs):
            raise ValueError("Some requested CERTs are absent from this snapshot.")

        def codes(values, label):
            if values is None:
                return None
            if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
                raise ValueError(f"{label} must be a nonempty sequence of codes.")
            if any(
                not isinstance(value, str)
                or not 1 <= len(value) <= 2
                or not value.isascii()
                or not value.isalpha()
                for value in values
            ):
                raise ValueError(f"Invalid {label} code.")
            result = sorted({value.upper() for value in values})
            if label == "states" and any(len(value) != 2 for value in result):
                raise ValueError("states requires two-letter abbreviations.")
            return result

        states, bank_classes = codes(states, "states"), codes(bank_classes, "bank_classes")
        for value in (min_assets_usd, max_assets_usd):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Asset bounds must be nonnegative integer dollars.")
        if (
            min_assets_usd is not None
            and max_assets_usd is not None
            and min_assets_usd >= max_assets_usd
        ):
            raise ValueError("min_assets_usd must be less than max_assets_usd.")
        identities = {bank["cert"]: bank for bank in self.document["banks"]}
        rows = []
        for row in self.document["rows"]:
            identity = identities[row["cert"]]
            if requested is not None and row["cert"] not in requested:
                continue
            if states is not None and identity.get("state") not in states:
                continue
            if bank_classes is not None and identity.get("bank_class") not in bank_classes:
                continue
            assets = row["assets_usd"]
            if min_assets_usd is not None and (assets is None or assets < min_assets_usd):
                continue
            if max_assets_usd is not None and (assets is None or assets >= max_assets_usd):
                continue
            rows.append(row)
        chosen = {row["cert"] for row in rows}
        return BankCohort.create(
            banks=[bank for bank in self.document["banks"] if bank["cert"] in chosen],
            rows=rows,
            dates=self.document["requested_dates"],
            sources=self.document["sources"],
            edition=self.document["edition"],
            selection={
                "type": "snapshot_filter",
                "parent_dataset_id": self.dataset_id,
                "anchor_report_date": self.document["requested_dates"][0],
                "parent_selection": self.document["selection"],
                "filters": {
                    "certs": requested,
                    "states": states,
                    "bank_classes": bank_classes,
                    "min_assets_usd": min_assets_usd,
                    "max_assets_usd_exclusive": max_assets_usd,
                },
            },
        )

    def to_pandas(self):
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError("Install us-bank-data[pandas] to use to_pandas().") from exc
        frame = pd.DataFrame(self.rows, columns=_columns())
        frame.attrs["usbankdata"] = self.manifest()
        return frame

    def to_polars(self):
        try:
            import polars as pl
        except ImportError as exc:
            raise ImportError("Install us-bank-data[polars] to use to_polars().") from exc
        # Explicit schema keeps all-null columns numeric and empty cohorts usable.
        schema = {
            "cert": pl.Int64,
            "bank_name": pl.String,
            "report_date": pl.String,
            "report_available": pl.Boolean,
        }
        schema.update(
            {
                key: pl.Int64 if _integer_column(key, item, self.document["rows"]) else pl.Float64
                for key, item in metric_definitions().items()
            }
        )
        return pl.DataFrame(self.rows, schema=schema)

    def export(self, path: str | Path) -> Path:
        self.validate()
        target = Path(path)
        if target.suffix.lower() not in {".json", ".csv", ".parquet"}:
            raise ValueError("Use a .json, .csv, or .parquet output filename.")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix.lower() == ".json":
            target.write_text(
                json.dumps(self.document, ensure_ascii=False, allow_nan=False) + "\n",
                encoding="utf-8",
            )
        elif target.suffix.lower() == ".csv":
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=_columns())
            writer.writeheader()
            writer.writerows(self.rows)
            raw = stream.getvalue().encode("utf-8")
            target.write_bytes(raw)
            receipt = dict(
                self.manifest(),
                artifact_filename=target.name,
                artifact_sha256=hashlib.sha256(raw).hexdigest(),
            )
            target.with_suffix(".manifest.json").write_text(
                json.dumps(receipt, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
            )
        else:
            try:
                import pyarrow as pa
                import pyarrow.parquet as pq
            except ImportError as exc:
                raise ImportError("Install us-bank-data[parquet] to export Parquet.") from exc
            schema = pa.schema(
                [
                    ("cert", pa.int64()),
                    ("bank_name", pa.string()),
                    ("report_date", pa.string()),
                    ("report_available", pa.bool_()),
                ]
                + [
                    (
                        key,
                        pa.int64()
                        if _integer_column(key, item, self.document["rows"])
                        else pa.float64(),
                    )
                    for key, item in metric_definitions().items()
                ]
            )
            table = pa.Table.from_pylist(self.rows, schema=schema)
            table = table.replace_schema_metadata(
                {b"usbankdata": canonical_json(self.manifest()).encode("utf-8")}
            )
            pq.write_table(table, target)
        return target

    @classmethod
    def load(cls, path: str | Path) -> BankCohort:
        try:
            obj = cls(json.loads(Path(path).read_text(encoding="utf-8")))
        except (ValueError, UnicodeError) as exc:
            raise DataError("Invalid cohort JSON.") from exc
        obj.validate()
        return obj


def _columns():
    return ["cert", "bank_name", "report_date", "report_available", *metric_definitions()]


def _integer_column(key, definition, rows):
    # Preserve any legitimate fractional count/dollar observation instead of
    # allowing a dataframe library to truncate it during an explicit cast.
    return definition["unit"] in {"USD", "count"} and all(
        row[key] is None or type(row[key]) is int for row in rows
    )


def _paged(
    client: FDICClient, dataset: str, params: dict, maximum: int
) -> tuple[list[dict], list[dict]]:
    rows, sources, expected, index = [], [], None, None
    for _ in range(MAX_BANKS + 1):
        page, source, total = client._get(
            dataset, dict(params, limit=100, offset=len(rows), sort_by="CERT", sort_order="ASC")
        )
        payload = json.loads(source["raw_json"])
        if type(payload.get("meta", {}).get("total")) is not int:
            raise DataError("FDIC did not provide an integer result count.")
        if expected is None:
            expected, index = total, source.get("source_index_name")
        if total != expected or source.get("source_index_name") != index or total > maximum:
            raise DataError(
                "FDIC pagination changed population/index or exceeded the requested cohort."
            )
        rows.extend(page)
        sources.append(source)
        if len(rows) == total:
            return rows, sources
        if len(rows) > total or not page:
            raise DataError("FDIC returned inconsistent pagination.")
    raise DataError("FDIC pagination exceeded its bounded request limit.")


def panel(
    certs: Sequence[int], *, through: str, quarters: int = 8, client: FDICClient | None = None
) -> BankCohort:
    """Fetch up to 100 explicit banks for one shared window (at most 40 quarters).

    Requests are grouped by quarter and sorted by CERT for stable pagination.
    Historical observations are not restricted to banks active today. Identity
    labels reflect the institutions endpoint at this retrieval, not each quarter.
    """
    selected = _certs(certs)
    dates = quarter_window(quarter_end(through), quarters)
    client = client or FDICClient()
    query = "CERT:(" + " OR ".join(map(str, selected)) + ")"
    identities, sources = _paged(
        client, "institutions", {"filters": query, "fields": INSTITUTION_FIELDS}, len(selected)
    )
    banks = [client._institution(row) for row in identities]
    if sorted(bank["cert"] for bank in banks) != selected:
        raise DataError("FDIC did not uniquely return every selected bank identity.")
    names = {bank["cert"]: bank["name"] for bank in banks}
    definitions = metric_definitions()
    fields = ",".join(["CERT", "REPDTE", *[item["source_field"] for item in definitions.values()]])
    rows = []
    for day in dates:
        raw_rows, evidence = _paged(
            client,
            "financials",
            {"filters": f"{query} AND REPDTE:{day.replace('-', '')}", "fields": fields},
            len(selected),
        )
        sources.extend(evidence)
        by_cert = {}
        for raw in raw_rows:
            cert = normalize_number(raw.get("CERT"))
            if cert not in names or source_date(raw.get("REPDTE")).isoformat() != day:
                raise DataError("FDIC returned a record outside the selected bank-quarter cohort.")
            if cert in by_cert:
                raise DataError("FDIC returned duplicate bank-quarter records.")
            if any(item["source_field"] not in raw for item in definitions.values()):
                raise DataError("FDIC omitted a requested metric field from a returned filing.")
            by_cert[cert] = raw
        for cert in selected:
            raw = by_cert.get(cert, {})
            result = {
                "cert": cert,
                "bank_name": names[cert],
                "report_date": day,
                "report_available": cert in by_cert,
            }
            result.update(
                {
                    key: normalize_number(raw.get(item["source_field"]), item["multiplier"])
                    for key, item in definitions.items()
                }
            )
            rows.append(result)
    return BankCohort.create(
        banks=banks,
        rows=rows,
        dates=dates,
        sources=sources,
        selection={"type": "explicit_certs", "certs": selected, "current_active_filter": False},
    )


def load_sample_cohort(certs: Sequence[int] = (628, 3510, 58665)) -> BankCohort:
    """Load the three legacy offline sample banks, not a representative peer group."""
    selected = _certs(certs)
    if set(selected) - {628, 3510, 58665}:
        raise ValueError("Offline eight-quarter samples exist only for CERT 628, 3510 and 58665.")
    samples = [load_sample(cert) for cert in selected]
    dates = samples[0].document["requested_dates"]
    for item in samples:
        item.validate()
        if item.document["requested_dates"] != dates:
            raise DataError("Offline samples have different reporting windows.")
    return BankCohort.create(
        banks=[item.document["bank"] for item in samples],
        rows=[row for item in samples for row in item.rows],
        dates=dates,
        sources=[source for item in samples for source in item.document["sources"]],
        selection={
            "type": "offline_interface_samples",
            "certs": selected,
            "purpose": "Examples across different bank sizes; not a matched or representative peer group.",
        },
    )
