"""Small, keyless FDIC client with bounded requests and explicit quarter coverage."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import BankPanel, DataError, metric_definitions, normalize_number

API = "https://api.fdic.gov/banks"
INSTITUTION_FIELDS = "CERT,NAME,CITY,STALP,RSSDID,ACTIVE,BKCLASS,DATEUPDT"


def quarter_end(value: str) -> date:
    """Accept an ISO quarter-end date or an explicit YYYYQn quarter."""
    if not isinstance(value, str):
        raise ValueError("through must be an ISO quarter-end date or YYYYQn.")
    match = re.fullmatch(r"(\d{4})Q([1-4])", value.upper())
    if match:
        year, quarter = map(int, match.groups())
        month = quarter * 3
        result = date(year, month, 31 if month in {3, 12} else 30)
    else:
        try:
            result = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("through must be an ISO quarter-end date or YYYYQn.") from exc
    if (result.month, result.day) not in {(3, 31), (6, 30), (9, 30), (12, 31)}:
        raise ValueError("through must be a calendar quarter-end.")
    return result


def source_date(value: Any) -> date:
    text = str(value)
    if re.fullmatch(r"\d{8}", text):
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    try:
        return quarter_end(text)
    except ValueError as exc:
        raise DataError(f"Invalid source report date: {value!r}") from exc


def quarter_window(through: date, quarters: int) -> list[str]:
    if isinstance(quarters, bool) or not isinstance(quarters, int) or not 1 <= quarters <= 40:
        raise ValueError("quarters must be an integer between 1 and 40.")
    index = through.year * 4 + through.month // 3 - 1
    result = []
    for current in range(index - quarters + 1, index + 1):
        year, offset = divmod(current, 4)
        month = (offset + 1) * 3
        result.append(date(year, month, 31 if month in {3, 12} else 30).isoformat())
    return result


def validate_cert(cert: int) -> int:
    if isinstance(cert, bool) or not isinstance(cert, int) or cert < 1:
        raise ValueError("cert must be a positive integer FDIC certificate identifier.")
    return cert


def http_get(url: str) -> bytes:
    """Retry only transient failures, with bounded timeout and backoff."""
    for attempt in range(3):
        try:
            request = Request(url, headers={"Accept": "application/json",
                                           "User-Agent": "BanksOnSale-Data/0.1.0 (+https://banksonsale.com)"})
            with urlopen(request, timeout=20) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code != 429 and not 500 <= exc.code < 600:
                raise DataError(f"FDIC rejected the request (HTTP {exc.code}).") from exc
            if attempt == 2:
                raise DataError(f"FDIC remains unavailable (HTTP {exc.code}).") from exc
            delay = 0.5 * 2 ** attempt
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            if retry_after and retry_after.isdigit():
                delay = min(10.0, max(delay, float(retry_after)))
            time.sleep(delay)
        except (URLError, TimeoutError) as exc:
            if attempt == 2:
                raise DataError("Could not reach FDIC; use load_sample() for the offline example.") from exc
            time.sleep(0.5 * 2 ** attempt)
    raise DataError("FDIC request failed.")


class FDICClient:
    """BanksOnSale's public-bank client. No account, key, or background telemetry."""

    def __init__(self, *, transport: Callable[[str], bytes] = http_get):
        self._transport = transport

    def _get(self, dataset: str, params: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
        url = f"{API}/{dataset}?{urlencode(dict(params, format='json'))}"
        raw = self._transport(url).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DataError("FDIC returned invalid JSON.") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise DataError("FDIC response has no data array.")
        rows = []
        for item in payload["data"]:
            if not isinstance(item, dict) or not isinstance(item.get("data"), dict):
                raise DataError("FDIC returned an invalid record.")
            rows.append(item["data"])
        meta = payload.get("meta", {})
        try:
            total = int(meta.get("total", len(rows)))
        except (ValueError, TypeError) as exc:
            raise DataError("FDIC returned an invalid result count.") from exc
        if total < len(rows) or (total > 0 and not rows):
            raise DataError("FDIC returned inconsistent or incomplete results.")
        source = {
            "agency": "FDIC", "dataset": dataset, "url": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "source_index_created_at": meta.get("index", {}).get("createTimestamp"),
            "source_index_name": meta.get("index", {}).get("name"),
            "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(), "raw_json": raw,
        }
        return rows, source, total

    def search(self, name: str, *, state: str | None = None, active: bool = True,
               limit: int = 20) -> list[dict[str, Any]]:
        """Find up to limit bank entities. Select a CERT explicitly from ambiguous matches."""
        tokens = re.findall(r"[^\W_]+", name, re.UNICODE) if isinstance(name, str) else []
        if not tokens:
            raise ValueError("Provide a bank name containing letters or numbers.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer between 1 and 100.")
        filters = [f"NAME:*{token.upper()}*" for token in tokens]
        if active:
            filters.append("ACTIVE:1")
        if state is not None:
            if not isinstance(state, str) or not re.fullmatch(r"[A-Za-z]{2}", state):
                raise ValueError("state must be a two-letter U.S. state or territory abbreviation.")
            filters.append(f"STALP:{state.upper()}")
        rows, _, _ = self._get("institutions", {
            "filters": " AND ".join(filters), "fields": INSTITUTION_FIELDS,
            "sort_by": "CERT", "sort_order": "ASC", "limit": limit,
        })
        return [self._institution(row) for row in rows]

    @staticmethod
    def _institution(row: dict[str, Any]) -> dict[str, Any]:
        cert = normalize_number(row.get("CERT"))
        if not isinstance(cert, int) or cert < 1:
            raise DataError("FDIC returned a missing or invalid bank identifier.")
        return {
            "cert": cert, "name": row.get("NAME"), "city": row.get("CITY"),
            "state": row.get("STALP"), "rssd_id": normalize_number(row.get("RSSDID")),
            "active": normalize_number(row.get("ACTIVE")) == 1,
            "source_updated_at": row.get("DATEUPDT"), "bank_class": row.get("BKCLASS"),
        }

    def bank(self, cert: int) -> Bank:
        return Bank(cert=validate_cert(cert), client=self)

    def panel(self, cert: int, *, quarters: int = 8, through: str | None = None) -> BankPanel:
        validate_cert(cert)
        # Validate inputs before making a network request.
        quarter_window(date(2026, 6, 30), quarters)
        end = quarter_end(through) if through is not None else None
        institutions, identity_source, _ = self._get("institutions", {
            "filters": f"CERT:{cert}", "fields": INSTITUTION_FIELDS, "limit": 2,
        })
        if len(institutions) != 1 or normalize_number(institutions[0].get("CERT")) != cert:
            raise DataError(f"FDIC bank CERT {cert} was not uniquely found.")
        identity = self._institution(institutions[0])
        sources = [identity_source]
        if end is None:
            latest, source, _ = self._get("financials", {
                "filters": f"CERT:{cert}", "fields": "CERT,REPDTE", "limit": 1,
                "sort_by": "REPDTE", "sort_order": "DESC",
            })
            sources.append(source)
            if not latest:
                raise DataError(f"No financial reports are available for FDIC bank CERT {cert}.")
            if normalize_number(latest[0].get("CERT")) != cert:
                raise DataError("The latest report belongs to a different bank.")
            end = source_date(latest[0].get("REPDTE"))
        dates = quarter_window(end, quarters)
        definitions = metric_definitions()
        field_names = ["CERT", "REPDTE"] + [item["source_field"] for item in definitions.values()]
        raw_rows, source, total = self._get("financials", {
            "filters": f"CERT:{cert} AND REPDTE:[{dates[0].replace('-', '')} TO {dates[-1].replace('-', '')}]",
            "fields": ",".join(field_names), "limit": 100, "sort_by": "REPDTE", "sort_order": "ASC",
        })
        sources.append(source)
        if total != len(raw_rows):
            raise DataError("FDIC truncated the requested bank-quarter panel.")
        by_date = {}
        for row in raw_rows:
            report_date = source_date(row.get("REPDTE")).isoformat()
            if normalize_number(row.get("CERT")) != cert or report_date not in dates:
                raise DataError("FDIC returned a record outside the requested bank-quarter window.")
            if report_date in by_date:
                raise DataError("FDIC returned duplicate bank-quarter records.")
            by_date[report_date] = row
        rows = []
        for report_date in dates:
            raw_row = by_date.get(report_date, {})
            result = {"cert": cert, "bank_name": identity["name"], "report_date": report_date,
                      "report_available": report_date in by_date}
            for key, definition in definitions.items():
                result[key] = normalize_number(raw_row.get(definition["source_field"]), definition["multiplier"])
            rows.append(result)
        return BankPanel.create(bank=identity, rows=rows, sources=sources, requested_dates=dates,
                                report_date_defaulted=through is None)


@dataclass(frozen=True)
class Bank:
    """An explicitly selected bank entity, identified by FDIC CERT."""

    cert: int
    client: FDICClient

    def financials(self, *, quarters: int = 8, through: str | None = None) -> BankPanel:
        return self.client.panel(self.cert, quarters=quarters, through=through)


def bank(cert: int) -> Bank:
    return FDICClient().bank(cert)


def search(name: str, *, state: str | None = None, active: bool = True,
           limit: int = 20) -> list[dict[str, Any]]:
    return FDICClient().search(name, state=state, active=active, limit=limit)
