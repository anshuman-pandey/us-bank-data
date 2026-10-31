"""Create a deterministic, reviewable plugin ZIP; never include local state."""
import argparse
import json
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1] / "plugins/us-bank-data"
allowed = ["plugin.json", "mcp.json", ".mcp.json", ".claude-plugin/plugin.json", "README.md", "LICENSE", "assets/icon.svg", "skills/us-bank-research/SKILL.md"]
manifest = json.loads((root / "plugin.json").read_text())
assert manifest["name"] == "us-bank-data" and manifest["version"] == "0.1.0"
assert json.loads((root / ".claude-plugin/plugin.json").read_text())["version"] == manifest["version"]
assert json.loads((root / "mcp.json").read_text())["mcpServers"]["us-bank-data"]["url"] == "https://www.banksonsale.com/api/mcp"
args.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for name in sorted(allowed):
        path = root / name
        assert path.is_file() and not path.is_symlink()
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 31, 0, 0, 0))
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, path.read_bytes())
print(f"Packaged {len(allowed)} allowlisted files: {args.output}")
