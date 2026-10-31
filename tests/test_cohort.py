"""Cohort population, financial-unit and source-integrity regression checks."""

import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from banksonsale_data.models import checksum
from usbankdata import (
    BankCohort,
    DataError,
    FDICClient,
    load_sample_cohort,
    metric_definitions,
    panel,
    snapshot,
)


def fixture_client(*, page_size=100, fault=None, employees=1):
    calls = []
    identities = [
        {
            "CERT": cert,
            "NAME": name,
            "CITY": "Example",
            "STALP": "NC",
            "RSSDID": cert * 10,
            "ACTIVE": active,
            "BKCLASS": "NM",
        }
        for cert, name, active in [(1, "Open Bank", 1), (2, "Closed Bank", 0)]
    ]

    def transport(url):
        calls.append(url)
        query = parse_qs(urlparse(url).query)
        if urlparse(url).path.endswith("/institutions"):
            rows = copy.deepcopy(identities)
            assert "ACTIVE:" not in query["filters"][0]
        else:
            day = query["filters"][0].split("REPDTE:")[1]
            rows = []
            for cert in [1, 2]:
                if day == "20260331" and cert == 2:
                    continue
                row = {item["source_field"]: 1 for item in metric_definitions().values()}
                row.update(
                    CERT=cert,
                    REPDTE=int(day),
                    ASSET=123456,
                    DEP=0,
                    ROA=-1.25,
                    EQ=None,
                    RBCT1CER=12.5,
                    RBC1AAJ=6.1,
                    NUMEMP=employees,
                )
                rows.append(row)
            if fault == "duplicate":
                rows = [rows[0], rows[0]]
            if fault == "outside":
                rows[0]["CERT"] = 999
            if fault == "date":
                rows[0]["REPDTE"] = 20250930
            if fault == "missing-field":
                rows[0].pop("ASSET")
        offset = int(query["offset"][0])
        total = len(rows) + (1 if fault == "total-change" and offset else 0)
        index = "changed" if fault == "index-change" and offset else "same-index"
        payload = {
            "meta": {"total": total, "index": {"name": index}},
            "data": [{"data": item} for item in rows[offset : offset + page_size]],
        }
        return json.dumps(payload).encode()

    return FDICClient(transport=transport), calls


def rehash(document):
    content = {
        key: value for key, value in document.items() if key not in {"content_sha256", "dataset_id"}
    }
    document["content_sha256"] = checksum(content)
    document["dataset_id"] = f"usbankdata-cohort-{document['content_sha256'][:16]}"


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = snapshot()

    def test_complete_source_population_and_units(self):
        data = self.snapshot
        self.assertEqual(len(data.rows), 4313)
        self.assertEqual(len(data.certs), 4313)
        self.assertEqual(data.document["coverage"]["reported_bank_quarters"], 4313)
        self.assertEqual(data.document["selection"]["bank_class_counts"]["NC"], 66)
        self.assertEqual(data.document["selection"]["bank_class_counts"]["OI"], 9)
        first = data.rows[0]
        self.assertEqual(first["cert"], 14)
        self.assertEqual(first["assets_usd"], 412620000000)
        self.assertEqual(first["cet1_ratio_pct"], 14.72)
        self.assertEqual(data.document["coverage"]["fields"]["cet1_ratio_pct"]["missing"], 1831)
        self.assertEqual(data.document["coverage"]["fields"]["deposits_usd"]["zero"], 58)

    def test_offline_and_deterministic(self):
        with patch(
            "urllib.request.urlopen", side_effect=AssertionError("Unexpected network request")
        ):
            self.assertEqual(snapshot().dataset_id, self.snapshot.dataset_id)
        for args in [{"quarter": "2026Q1"}, {"edition": "latest"}, {"quarter": "2026-07-01"}]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                snapshot(**args)

    def test_filter_anchor_boundaries_and_missing(self):
        first = self.snapshot.rows[0]
        n = first["assets_usd"]
        selected = self.snapshot.select(certs=[14], min_assets_usd=n, max_assets_usd=n + 1)
        self.assertEqual(selected.certs, [14])
        self.assertEqual(selected.document["selection"]["anchor_report_date"], "2026-06-30")
        self.assertEqual(self.snapshot.select(certs=[14], max_assets_usd=n).certs, [])
        self.assertEqual(len(self.snapshot.select(bank_classes=["NC"]).rows), 66)
        self.assertTrue(
            all(bank["state"] == "NC" for bank in self.snapshot.select(states=["nc"]).banks)
        )
        for args in [
            {"certs": [999999]},
            {"states": "NC"},
            {"states": ["N"]},
            {"min_assets_usd": True},
            {"max_assets_usd": -1},
            {"min_assets_usd": 2, "max_assets_usd": 1},
            {"certs": [14, 14]},
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.snapshot.select(**args)

    def test_source_and_content_tampering_rejected(self):
        document = self.snapshot.to_dict()
        document["rows"][0]["assets_usd"] += 1000
        with self.assertRaises(DataError):
            BankCohort(document).validate()
        document = self.snapshot.to_dict()
        document["sources"][0]["raw_json"] += " "
        rehash(document)
        with self.assertRaisesRegex(DataError, "archived source"):
            BankCohort(document).validate()

    def test_exports_round_trip_and_zero_rows(self):
        selected = self.snapshot.select(certs=[14, 58665])
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            selected.export(directory / "data.json")
            self.assertEqual(BankCohort.load(directory / "data.json").to_dict(), selected.to_dict())
            selected.export(directory / "data.csv")
            receipt = json.loads((directory / "data.manifest.json").read_text())
            self.assertEqual(
                receipt["artifact_sha256"],
                hashlib.sha256((directory / "data.csv").read_bytes()).hexdigest(),
            )
            self.assertEqual(
                len(list(csv.DictReader((directory / "data.csv").read_text().splitlines()))), 2
            )
            empty = self.snapshot.select(states=["ZZ"])
            empty.export(directory / "empty.csv")
            self.assertEqual(
                len(list(csv.DictReader((directory / "empty.csv").read_text().splitlines()))), 0
            )

    def test_returned_records_are_independent(self):
        rows = self.snapshot.rows
        rows[0]["assets_usd"] = 0
        self.assertNotEqual(rows[0]["assets_usd"], self.snapshot.rows[0]["assets_usd"])


class LiveCohortTests(unittest.TestCase):
    def test_aligned_population_includes_inactive_and_preserves_null_zero_negative(self):
        client, calls = fixture_client()
        data = panel([2, 1], through="2026Q2", quarters=2, client=client)
        self.assertEqual(len(calls), 3)  # one identity batch plus two quarter batches
        self.assertEqual(data.certs, [1, 2])
        self.assertEqual(len(data.rows), 4)
        self.assertEqual(data.document["coverage"]["reported_bank_quarters"], 3)
        missing = [row for row in data.rows if not row["report_available"]]
        self.assertEqual(
            [(row["cert"], row["report_date"]) for row in missing], [(2, "2026-03-31")]
        )
        self.assertTrue(all(missing[0][key] is None for key in metric_definitions()))
        observed = data.rows[0]
        self.assertEqual(observed["assets_usd"], 123456000)
        self.assertEqual(observed["deposits_usd"], 0)
        self.assertIsNone(observed["equity_usd"])
        self.assertEqual(observed["roa_pct"], -1.25)
        self.assertEqual(observed["cet1_ratio_pct"], 12.5)
        self.assertEqual(observed["leverage_ratio_pct"], 6.1)
        self.assertFalse(data.banks[1]["active"])
        with self.assertRaises(ValueError):
            data.select(states=["NC"])

    def test_pagination(self):
        client, calls = fixture_client(page_size=1)
        data = panel([1, 2], through="2026Q2", quarters=1, client=client)
        self.assertEqual(len(data.rows), 2)
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(data.document["sources"]), 4)

    def test_bad_pagination_and_source_rows_rejected(self):
        for fault in [
            "duplicate",
            "outside",
            "date",
            "missing-field",
            "total-change",
            "index-change",
        ]:
            with self.subTest(fault=fault):
                client, _ = fixture_client(page_size=1, fault=fault)
                with self.assertRaises(DataError):
                    panel([1, 2], through="2026Q2", quarters=1, client=client)

    def test_invalid_arguments_fail_before_network(self):
        for args in [
            {"certs": []},
            {"certs": [True]},
            {"certs": [1, 1]},
            {"certs": list(range(1, 102))},
            {"certs": "1"},
            {"certs": [1], "quarters": 41},
            {"certs": [1], "through": "2026-07-01"},
        ]:
            client, calls = fixture_client()
            values = dict(through="2026Q2", quarters=1, client=client)
            values.update(args)
            with self.subTest(args=args), self.assertRaises(ValueError):
                panel(**values)
            self.assertEqual(calls, [])

    def test_schema_checks_even_with_recomputed_content_hash(self):
        data = load_sample_cohort()
        for mutate in [
            lambda d: d["rows"].pop(),
            lambda d: d["rows"][0].update(report_available="false"),
            lambda d: d["coverage"].update(banks=999),
            lambda d: d["rows"][0].update(assets_usd=True),
            lambda d: d["metric_definitions"]["assets_usd"].update(multiplier=1),
        ]:
            doc = data.to_dict()
            mutate(doc)
            rehash(doc)
            with self.assertRaises(DataError):
                BankCohort(doc).validate()

    def test_sample_cohort(self):
        data = load_sample_cohort()
        self.assertEqual(len(data.rows), 24)
        self.assertEqual(data.certs, [628, 3510, 58665])
        self.assertEqual(data.document["requested_dates"][0], "2024-09-30")
        self.assertEqual(data.document["requested_dates"][-1], "2026-06-30")
        self.assertEqual(data.document["selection"]["type"], "offline_interface_samples")
        with self.assertRaises(ValueError):
            load_sample_cohort([14])


class OptionalCohortIOTests(unittest.TestCase):
    @unittest.skipUnless(
        importlib.util.find_spec("polars") and importlib.util.find_spec("pyarrow"),
        "optional polars/pyarrow not installed",
    )
    def test_fractional_observation_is_not_truncated(self):
        import polars as pl
        import pyarrow as pa
        import pyarrow.parquet as pq

        client, _ = fixture_client(employees=1.5)
        data = panel([1, 2], through="2026Q2", quarters=1, client=client)
        self.assertEqual(data.rows[0]["employees"], 1.5)
        self.assertEqual(data.to_polars().schema["employees"], pl.Float64)
        self.assertEqual(data.to_polars()["employees"][0], 1.5)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "fractional.parquet"
            data.export(target)
            table = pq.read_table(target)
            self.assertEqual(table.schema.field("employees").type, pa.float64())
            self.assertEqual(table["employees"][0].as_py(), 1.5)

    @unittest.skipUnless(importlib.util.find_spec("polars"), "optional polars not installed")
    def test_polars_and_empty_schema(self):
        import polars as pl

        data = snapshot().select(certs=[14])
        self.assertEqual(data.to_polars()["assets_usd"][0], 412620000000)
        empty = data.select(states=["ZZ"]).to_polars()
        self.assertEqual(empty.height, 0)
        self.assertEqual(empty.schema["assets_usd"], pl.Int64)

    @unittest.skipUnless(importlib.util.find_spec("pandas"), "optional pandas not installed")
    def test_pandas_evidence(self):
        data = load_sample_cohort()
        frame = data.to_pandas()
        self.assertEqual(len(frame), 24)
        self.assertEqual(frame.attrs["usbankdata"]["dataset_id"], data.dataset_id)

    @unittest.skipUnless(importlib.util.find_spec("pyarrow"), "optional pyarrow not installed")
    def test_parquet_receipt_and_types(self):
        import pyarrow as pa
        import pyarrow.parquet as pq

        data = snapshot().select(certs=[14])
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "data.parquet"
            data.export(target)
            table = pq.read_table(target)
            self.assertEqual(table["assets_usd"][0].as_py(), 412620000000)
            self.assertEqual(table.schema.field("assets_usd").type, pa.int64())
            self.assertEqual(
                json.loads(table.schema.metadata[b"usbankdata"])["dataset_id"], data.dataset_id
            )


if __name__ == "__main__":
    unittest.main()
