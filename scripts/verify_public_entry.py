"""Check that the new public import uses the unchanged financial implementation."""
import json
import subprocess
import sys

import banksonsale_data as engine
import usbankdata as public

for name in engine.__all__:
    if name != "__version__":
        assert getattr(public, name) is getattr(engine, name), name
assert public.load_sample().to_dict() == engine.load_sample().to_dict()
old = json.loads(subprocess.check_output([sys.executable, "-m", "banksonsale_data", "sample"], text=True))
new = json.loads(subprocess.check_output([sys.executable, "-m", "usbankdata", "sample"], text=True))
assert old == new
print(json.dumps({"public_import": "usbankdata", "version": public.__version__,
                  "financial_implementation": "unchanged", "cli_output": "identical"}))
