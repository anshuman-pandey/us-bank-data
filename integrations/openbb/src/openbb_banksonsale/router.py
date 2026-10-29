"""BanksOnSale bank data in OpenBB's Python client and REST API."""

import asyncio
from typing import Any

from banksonsale_data import bank, load_sample, metric_definitions, search
from openbb_core.app.model.obbject import OBBject
from openbb_core.app.router import Router

router = Router(prefix="", description="BanksOnSale: source-linked U.S. bank research data.")


@router.command(methods=["GET"])
async def lookup(name: str, state: str | None = None, limit: int = 20) -> OBBject[list[dict[str, Any]]]:
    """Search bank entities by name; choose an FDIC CERT explicitly from the matches."""
    matches = await asyncio.to_thread(search, name, state=state, limit=limit)
    return OBBject(results=matches, extra={"banksonsale": {"publisher": "BanksOnSale",
                                                         "publisher_url": "https://banksonsale.com"}})


@router.command(methods=["GET"])
async def financials(cert: int, quarters: int = 8,
                     through: str | None = None) -> OBBject[list[dict[str, Any]]]:
    """Get a bank's calendar-quarter panel, with definitions and archived FDIC evidence."""
    panel = await asyncio.to_thread(bank(cert).financials, quarters=quarters, through=through)
    return OBBject(results=panel.rows, extra={"banksonsale": panel.manifest()})


@router.command(methods=["GET"])
async def sample(cert: int = 58665) -> OBBject[list[dict[str, Any]]]:
    """Load a pinned real-bank example without network access. CERTs: 628, 3510, 58665."""
    panel = load_sample(cert)
    return OBBject(results=panel.rows, extra={"banksonsale": panel.manifest()})


@router.command(methods=["GET"])
async def definitions() -> OBBject[list[dict[str, Any]]]:
    """Show BanksOnSale's metric units, reporting bases, and FDIC source fields."""
    return OBBject(results=list(metric_definitions().values()),
                  extra={"banksonsale": {"publisher": "BanksOnSale", "publisher_url": "https://banksonsale.com"}})
