"""Extract the existing, pinned source edition for offline MCP protocol tests."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
target = root / "integrations/mcp/test/fixtures"
target.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(root / "packages/us-bank-data/src/usbankdata/resources/2026-q2-r1.zip") as archive:
    for name in ("financials.json", "manifest.json"):
        (target / name).write_bytes(archive.read(name))
print("Prepared MCP fixtures from the pinned Python package snapshot")
