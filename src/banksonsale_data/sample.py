"""Pinned, source-archived BanksOnSale examples that work without network access."""

import json
from importlib.resources import files

from .client import validate_cert
from .models import BankPanel


def load_sample(cert: int = 58665) -> BankPanel:
    """Load one of three real, pinned sample banks; no source requests are made."""
    validate_cert(cert)
    resource = files("banksonsale_data").joinpath(f"resources/sample-{cert}.json")
    if not resource.is_file():
        raise ValueError("Sample CERTs are 628, 3510, and 58665. Use bank(cert) for another bank.")
    panel = BankPanel(json.loads(resource.read_text(encoding="utf-8")))
    panel.validate()
    return panel
