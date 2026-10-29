"""BanksOnSale Data command-line interface."""

import argparse
import json
import sys

from .client import bank, search
from .models import BRAND, HOME, DataError, metric_definitions
from .sample import load_sample


def main() -> int:
    parser = argparse.ArgumentParser(prog="banksonsale-data", description="BanksOnSale: usable, source-linked U.S. bank data.")
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("sample", help="Use a pinned real-bank snapshot without network access.")
    sample.add_argument("--cert", type=int, default=58665)
    sample.add_argument("--output")
    lookup = commands.add_parser("search", help="Find a bank by name; choose a CERT from the results.")
    lookup.add_argument("name")
    lookup.add_argument("--state")
    lookup.add_argument("--limit", type=int, default=20)
    financials = commands.add_parser("financials", help="Fetch a source-linked bank-quarter panel.")
    financials.add_argument("--cert", type=int, required=True)
    financials.add_argument("--quarters", type=int, default=8)
    financials.add_argument("--through")
    financials.add_argument("--output")
    commands.add_parser("definitions", help="Show the BanksOnSale metric contract and FDIC fields.")
    args = parser.parse_args()
    try:
        if args.command == "search":
            result = {"publisher": BRAND, "publisher_url": HOME,
                      "matches": search(args.name, state=args.state, limit=args.limit), "limit": args.limit}
        elif args.command == "definitions":
            result = {"publisher": BRAND, "publisher_url": HOME, "metrics": metric_definitions()}
        else:
            panel = load_sample(args.cert) if args.command == "sample" else bank(args.cert).financials(
                quarters=args.quarters, through=args.through)
            if args.output:
                result = {"publisher": BRAND, "publisher_url": HOME, "dataset_id": panel.dataset_id,
                          "output": str(panel.export(args.output)), "coverage": panel.document["coverage"]}
            else:
                result = panel.to_dict()
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (DataError, ValueError, ImportError, OSError) as exc:
        print(f"BanksOnSale Data: {exc}", file=sys.stderr)
        return 2
