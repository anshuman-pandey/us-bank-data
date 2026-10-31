"""A pinned, offline quarter-wide edition with the original FDIC responses."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections import Counter
from importlib.resources import files

from banksonsale_data import DataError, metric_definitions
from banksonsale_data.client import quarter_end, source_date
from banksonsale_data.models import normalize_number

from ._editions import EDITIONS
from .cohort import BankCohort


def snapshot(*, quarter: str = "2026Q2", edition: str = "2026-q2-r1") -> BankCohort:
    """Load the bundled 4,313-record 2026Q2 edition without network access.

    Includes NC and OI institution classes; not an insured-only or current-active
    universe. No automatic latest-data selection. Monetary source values in USD
    thousands are converted once to the package's dollar columns.
    """
    day = quarter_end(quarter).isoformat()
    if edition not in EDITIONS or EDITIONS[edition]["report_date"] != day:
        raise ValueError("This release bundles only quarter 2026Q2, edition 2026-q2-r1.")
    descriptor = EDITIONS[edition]
    archive = files("usbankdata").joinpath("resources", descriptor["file"]).read_bytes()
    if hashlib.sha256(archive).hexdigest() != descriptor["sha256"]:
        raise DataError("The bundled edition archive does not match its pinned checksum.")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            manifest_raw = bundle.read("manifest.json")
            manifest = json.loads(manifest_raw)
            if (
                manifest["release"] != edition
                or manifest["report_date"] != day
                or manifest["schema_version"] != "1.0.0"
            ):
                raise DataError("Unsupported bundled source-edition schema.")
            raw = bundle.read("financials.json")
            expected_file = next(
                item for item in manifest["files"] if item["file"] == "financials.json"
            )
            if (
                hashlib.sha256(raw).hexdigest() != expected_file["sha256"]
                or len(raw) != expected_file["bytes"]
            ):
                raise DataError("The source-edition data hash or size does not match.")
            records = json.loads(raw)
            definitions = metric_definitions()
            originals, sources = {}, []
            for source in manifest["sources"]:
                evidence = bundle.read(source["file"])
                if hashlib.sha256(evidence).hexdigest() != source["sha256"]:
                    raise DataError("An original FDIC archive does not match its source hash.")
                payload = json.loads(evidence)
                if (
                    payload["meta"]["total"] != manifest["record_count"]
                    or len(payload["data"]) != source["records"]
                ):
                    raise DataError("An original FDIC archive has inconsistent coverage.")
                for item in payload["data"]:
                    record = item["data"]
                    cert = normalize_number(record["CERT"])
                    if cert in originals or source_date(record["REPDTE"]).isoformat() != day:
                        raise DataError("Duplicate or out-of-period original FDIC record.")
                    originals[cert] = record
                sources.append(
                    {
                        "agency": "FDIC",
                        "dataset": "financials",
                        "url": source["url"],
                        "retrieved_at": source["retrieved_at"],
                        "sha256": source["sha256"],
                        "source_index_name": source.get("index", {}).get("name"),
                        "source_index_created_at": source.get("index", {}).get("createTimestamp"),
                        "raw_json": evidence.decode("utf-8"),
                    }
                )
            if len(records) != manifest["record_count"] or len(originals) != len(records):
                raise DataError("The bundled snapshot is incomplete.")
            banks, rows, seen = [], [], set()
            for record in records:
                cert = record["cert"]
                if (
                    type(cert) is not int
                    or cert < 1
                    or cert in seen
                    or record["report_date"] != day
                    or cert not in originals
                ):
                    raise DataError("Invalid or duplicate compiled bank-quarter key.")
                seen.add(cert)
                original = originals[cert]
                if record["name"] != (original.get("NAMEFULL") or original.get("NAME")) or record[
                    "state"
                ] != original.get("STALP"):
                    raise DataError(
                        "Compiled institution labels differ from their archived source."
                    )
                identity = {
                    "cert": cert,
                    "name": record["name"],
                    "city": record["city"],
                    "state": record["state"],
                    "rssd_id": record["rssd_id"],
                    "bank_class": record["bank_class"],
                    "active_in_source": record["active_in_source"],
                }
                banks.append(identity)
                row = {
                    "cert": cert,
                    "bank_name": record["name"],
                    "report_date": day,
                    "report_available": True,
                }
                for key, definition in definitions.items():
                    field = definition["source_field"]
                    if (
                        field not in record
                        or field not in original
                        or normalize_number(record[field]) != normalize_number(original[field])
                    ):
                        raise DataError(f"Compiled {field} differs from its archived source.")
                    row[key] = normalize_number(record[field], definition["multiplier"])
                rows.append(row)
            if dict(Counter(bank["bank_class"] for bank in banks)) != manifest["bank_class_counts"]:
                raise DataError("The institution-class population differs from its manifest.")
            for definition in definitions.values():
                field = definition["source_field"]
                values = [normalize_number(record[field]) for record in records]
                coverage = {
                    "reported": sum(value is not None for value in values),
                    "missing": sum(value is None for value in values),
                    "zero": sum(value == 0 for value in values),
                }
                if coverage != manifest["coverage"][field]:
                    raise DataError(f"Source coverage mismatch for {field}.")
            # The original edition manifest is also an archived source, preserving
            # publisher, licensing, scope, raw units and download checksums.
            sources.append(
                {
                    "agency": "BanksOnSale",
                    "dataset": "edition_manifest",
                    "url": f"https://www.banksonsale.com/data/releases/{edition}/manifest.json",
                    "published_at": manifest["published_at"],
                    "raw_json": manifest_raw.decode("utf-8"),
                    "sha256": hashlib.sha256(manifest_raw).hexdigest(),
                }
            )
            return BankCohort.create(
                banks=banks,
                rows=rows,
                dates=[day],
                sources=sources,
                selection={
                    "type": "published_quarter_population",
                    "scope": manifest["scope"],
                    "current_active_filter": False,
                    "bank_class_counts": manifest["bank_class_counts"],
                },
                edition={
                    "id": edition,
                    "report_date": day,
                    "published_at": manifest["published_at"],
                    "source_retrieved_at": manifest["retrieved_at"],
                    "bundle_sha256": descriptor["sha256"],
                    "license": manifest["license"],
                    "license_scope": manifest["license_scope"],
                    "credit": "BanksOnSale compilation and original metadata, sourced from FDIC BankFind Suite.",
                },
            )
    except (KeyError, ValueError, TypeError, zipfile.BadZipFile, StopIteration) as exc:
        raise DataError("Malformed bundled FDIC snapshot edition.") from exc
