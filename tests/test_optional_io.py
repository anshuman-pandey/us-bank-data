import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from banksonsale_data import load_sample


class OptionalIOTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("pandas"), "pandas optional extra not installed")
    def test_pandas_retains_banksonsale_evidence(self):
        panel = load_sample()
        frame = panel.to_pandas()
        self.assertEqual(len(frame), 8)
        self.assertEqual(frame.attrs["banksonsale"]["dataset_id"], panel.dataset_id)

    @unittest.skipUnless(importlib.util.find_spec("polars"), "Polars optional extra not installed")
    def test_polars_preserves_the_reported_observations(self):
        panel = load_sample()
        frame = panel.to_polars()
        self.assertEqual(frame.height, 8)
        self.assertEqual(frame["assets_usd"].to_list(), [row["assets_usd"] for row in panel.rows])
        self.assertEqual(panel.manifest()["publisher"], "BanksOnSale")

    @unittest.skipUnless(importlib.util.find_spec("pyarrow"), "Parquet optional extra not installed")
    def test_parquet_preserves_units_and_source_evidence(self):
        import pyarrow.parquet as pq
        panel = load_sample()
        with tempfile.TemporaryDirectory() as directory:
            path = panel.export(Path(directory) / "banksonsale.parquet")
            table = pq.read_table(path)
            manifest = json.loads(table.schema.metadata[b"banksonsale"])
            self.assertEqual(table.num_rows, 8)
            self.assertEqual(manifest["publisher"], "BanksOnSale")
            self.assertEqual(manifest["metric_definitions"]["assets_usd"]["unit"], "USD")
            self.assertTrue(manifest["sources"])


if __name__ == "__main__":
    unittest.main()
