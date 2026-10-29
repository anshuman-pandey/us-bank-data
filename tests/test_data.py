import copy
import hashlib
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from banksonsale_data import BankPanel, DataError, FDICClient, load_sample, metric_definitions
from banksonsale_data.client import http_get, quarter_end, quarter_window
from banksonsale_data.models import checksum, normalize_number


class SourceTransport:
    """Independent minimal upstream records, including absence and a missing quarter."""

    def __init__(self, rows=None, total=None):
        self.calls = []
        self.rows = rows if rows is not None else [
            {"CERT": 58665, "REPDTE": "20260630", "ASSET": "12500", "DEP": 10000,
             "EQ": -50, "INTAN": None, "ROA": 0, "RBCT1CER": 11, "RBC1AAJ": 7},
            {"CERT": 58665, "REPDTE": "20251231", "ASSET": 12000, "EQ": 0},
        ]
        self.total = total

    def __call__(self, url):
        self.calls.append(url)
        params = parse_qs(urlparse(url).query)
        if urlparse(url).path.endswith("institutions"):
            rows = [{"CERT": 58665, "NAME": "Example Bank", "CITY": "Wilmington",
                     "STALP": "NC", "RSSDID": 123, "ACTIVE": 1}]
        elif params["limit"] == ["1"]:
            rows = [{"CERT": 58665, "REPDTE": "20260630"}]
        else:
            rows = self.rows
        total = len(rows) if self.total is None or params["limit"] != ["100"] else self.total
        return json.dumps({"data": [{"data": row} for row in rows],
                           "meta": {"total": total, "index": {"createTimestamp": "2026-08-19T00:00:00Z"}}}).encode()


class DataContractTests(unittest.TestCase):
    def test_money_units_and_capital_fields(self):
        panel = FDICClient(transport=SourceTransport()).panel(58665, quarters=3)
        latest = panel.rows[-1]
        self.assertEqual(latest["assets_usd"], 12_500_000)
        self.assertEqual(latest["equity_usd"], -50_000)
        self.assertEqual(latest["cet1_ratio_pct"], 11)
        self.assertEqual(latest["leverage_ratio_pct"], 7)
        self.assertEqual(metric_definitions()["cet1_ratio_pct"]["source_field"], "RBCT1CER")
        self.assertEqual(metric_definitions()["leverage_ratio_pct"]["source_field"], "RBC1AAJ")

    def test_absence_and_zero_do_not_converge(self):
        panel = FDICClient(transport=SourceTransport()).panel(58665, quarters=3)
        self.assertEqual(panel.rows[0]["equity_usd"], 0)
        self.assertIsNone(panel.rows[0]["deposits_usd"])
        self.assertEqual(panel.rows[-1]["roa_pct"], 0)
        self.assertIsNone(panel.rows[-1]["intangibles_usd"])

    def test_missing_quarter_is_not_filled_with_an_older_report(self):
        panel = FDICClient(transport=SourceTransport()).panel(58665, quarters=3)
        self.assertEqual(panel.document["requested_dates"], ["2025-12-31", "2026-03-31", "2026-06-30"])
        self.assertFalse(panel.rows[1]["report_available"])
        self.assertIsNone(panel.rows[1]["assets_usd"])
        self.assertEqual(panel.document["coverage"]["missing_quarters"], ["2026-03-31"])

    def test_explicit_quarter_does_not_query_latest(self):
        transport = SourceTransport()
        panel = FDICClient(transport=transport).panel(58665, quarters=3, through="2026Q2")
        self.assertEqual(len(transport.calls), 2)
        self.assertFalse(panel.document["report_date_defaulted"])

    def test_quarter_boundaries_and_year_rollover(self):
        self.assertEqual(quarter_end("2026q2"), date(2026, 6, 30))
        self.assertEqual(quarter_window(date(2026, 3, 31), 2), ["2025-12-31", "2026-03-31"])
        for invalid in ["2026-06-29", "2026Q5", "nonsense"]:
            with self.assertRaises(ValueError):
                quarter_end(invalid)

    def test_invalid_inputs_fail_before_network(self):
        transport = SourceTransport()
        client = FDICClient(transport=transport)
        for cert in [True, 0, -1, "628"]:
            with self.assertRaises(ValueError):
                client.panel(cert)
        for quarters in [True, 0, 41, 2.5]:
            with self.assertRaises(ValueError):
                client.panel(628, quarters=quarters)
        with self.assertRaises(ValueError):
            client.panel(628, through="2026-06-29")
        self.assertEqual(transport.calls, [])

    def test_foreign_bank_out_of_range_and_duplicate_reports_fail(self):
        for rows in [
            [{"CERT": 3510, "REPDTE": "20260630"}],
            [{"CERT": 58665, "REPDTE": "20250930"}],
            [{"CERT": 58665, "REPDTE": "20260630"}] * 2,
        ]:
            with self.assertRaises(DataError):
                FDICClient(transport=SourceTransport(rows=rows)).panel(58665, quarters=3)

    def test_truncated_results_and_invalid_numeric_values_fail(self):
        with self.assertRaises(DataError):
            FDICClient(transport=SourceTransport(total=10)).panel(58665, quarters=3)
        for invalid in ["oops", "Infinity", True]:
            with self.assertRaises(DataError):
                normalize_number(invalid)
        self.assertEqual(normalize_number("12.5", 1000), 12500)
        self.assertIsNone(normalize_number("NA"))

    def test_lookup_never_accepts_raw_query_syntax(self):
        transport = SourceTransport()
        FDICClient(transport=transport).search('First "National"', state="nc")
        filters = parse_qs(urlparse(transport.calls[0]).query)["filters"][0]
        self.assertEqual(filters, "NAME:*FIRST* AND NAME:*NATIONAL* AND ACTIVE:1 AND STALP:NC")
        with self.assertRaises(ValueError):
            FDICClient(transport=transport).search("Bank", state="NC OR ACTIVE:0")

    def test_json_roundtrip_and_change_detection(self):
        panel = FDICClient(transport=SourceTransport()).panel(58665, quarters=3)
        with tempfile.TemporaryDirectory() as directory:
            path = panel.export(Path(directory) / "banksonsale.json")
            self.assertEqual(BankPanel.load(path).rows, panel.rows)
            changed = panel.to_dict()
            changed["rows"][-1]["assets_usd"] += 1
            with self.assertRaises(DataError):
                BankPanel(changed).validate()

    def test_dataset_identity_cannot_be_changed_without_detection(self):
        panel = FDICClient(transport=SourceTransport()).panel(58665, quarters=3)
        changed = panel.to_dict()
        changed["dataset_id"] = "banksonsale-fdic-628-wrong"
        with self.assertRaises(DataError):
            BankPanel(changed).validate()

    def test_archived_source_change_detection(self):
        panel = FDICClient(transport=SourceTransport()).panel(58665, quarters=3)
        changed = panel.to_dict()
        changed["sources"][0]["raw_json"] += " "
        changed["content_sha256"] = checksum({key: value for key, value in changed.items() if key not in {"content_sha256", "dataset_id"}})
        with self.assertRaises(DataError):
            BankPanel(changed).validate()

    def test_csv_carries_a_branded_checksummed_source_manifest(self):
        panel = FDICClient(transport=SourceTransport()).panel(58665, quarters=3)
        with tempfile.TemporaryDirectory() as directory:
            path = panel.export(Path(directory) / "banksonsale.csv")
            manifest = json.loads(path.with_suffix(".manifest.json").read_text())
            self.assertEqual(manifest["publisher"], "BanksOnSale")
            self.assertEqual(manifest["artifact_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertTrue(manifest["sources"])

    def test_reading_rows_cannot_modify_the_pinned_dataset(self):
        panel = FDICClient(transport=SourceTransport()).panel(58665, quarters=3)
        rows = panel.rows
        rows[0]["assets_usd"] = 999
        self.assertNotEqual(rows, panel.rows)
        panel.validate()

    def test_all_real_samples_have_original_source_evidence(self):
        for cert in [628, 3510, 58665]:
            panel = load_sample(cert)
            self.assertEqual(len(panel.rows), 8)
            self.assertEqual(panel.document["coverage"]["reported_quarters"], 8)
            self.assertTrue(all(source["raw_json"] for source in panel.document["sources"]))
            raw = json.loads(panel.document["sources"][-1]["raw_json"])
            source_rows = {str(item["data"]["REPDTE"]): item["data"] for item in raw["data"]}
            for row in panel.rows:
                source = source_rows[row["report_date"].replace("-", "")]
                for name, definition in metric_definitions().items():
                    self.assertEqual(row[name], normalize_number(source.get(definition["source_field"]), definition["multiplier"]))

    def test_client_does_not_retry_a_permanent_http_error(self):
        error = HTTPError("https://api.fdic.gov/banks/financials", 400, "Bad request", {}, io.BytesIO())
        with patch("banksonsale_data.client.urlopen", side_effect=error) as request, patch("banksonsale_data.client.time.sleep") as sleep:
            with self.assertRaises(DataError):
                http_get(error.url)
            self.assertEqual(request.call_count, 1)
            sleep.assert_not_called()

    def test_transient_http_error_is_retried_with_a_bound(self):
        error = HTTPError("https://api.fdic.gov/banks/financials", 429, "Rate limited", {"Retry-After": "9999"}, io.BytesIO())
        with patch("banksonsale_data.client.urlopen", side_effect=error) as request, patch("banksonsale_data.client.time.sleep") as sleep:
            with self.assertRaises(DataError):
                http_get(error.url)
            self.assertEqual(request.call_count, 3)
            self.assertTrue(all(call.args[0] <= 10 for call in sleep.call_args_list))


if __name__ == "__main__":
    unittest.main()
