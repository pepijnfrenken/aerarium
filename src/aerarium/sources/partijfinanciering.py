"""partijfinanciering.nl adapter (BZK, Dashboard partijfinanciering).

Three endpoints, three shapes:

  POST /v1/graphql                 jaarverslagen document index (92 rows, 2020-2024)
  GET  /dashboard/subsidies        Wfpp subsidy per party per year, server-rendered, two tables
  GET  /dashboard/jaarlijkse-verantwoording/giften/{jaar}
                                   gifts of EUR 1.000+ per party, server-rendered, one card per party

Amounts here are euros (bedrag_eur), NOT thousands; the Dutch format is unambiguous:
'.' separates thousands, ',' separates decimals. A '-' cell means the party was not entitled or not
paid that year: NULL with its own status, never 0. An empty year (zero parties, total 0,00) is
no-data-published, never a zero year. The 92 PDFs behind `link` are NOT downloaded here.

No licence statement was found on partijfinanciering.nl or in the open.overheid.nl shell; the
licence is recorded as such rather than claimed as CC-0.
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import requests

from .rijksfinancien import Fetched

GRAPHQL_URL = "https://api.partijfinanciering.nl/v1/graphql"
SITE = "https://www.partijfinanciering.nl"
SUBSIDIES_URL = f"{SITE}/dashboard/subsidies"
GIFTEN_URL = f"{SITE}/dashboard/jaarlijkse-verantwoording/giften"

JAARVERSLAGEN_QUERY = (
    "{ jaarverslagen(order_by:[{jaar:desc},{partij:asc}], limit:200) "
    "{ partij jaar deel datum pages bestand_grootte_mb link } }"
)

LICENCE = "geen licentieverklaring aangetroffen (partijfinanciering.nl / open.overheid.nl)"
USER_AGENT = "aerarium/0.1 (party-funding provenance research)"

STATUS_PRESENT = "documented"
STATUS_NOT_ENTITLED = "not-entitled-or-not-paid"
STATUS_NO_DATA = "no-data-published"

_MONEY = r"(?:<!--\s*-->)?\s*([\d.,]+)"


def parse_eur(text: str) -> Decimal:
    """Dutch-formatted euros to Decimal. '€ 28.873.282' -> 28873282; '€ 567.307,6' -> 567307.6."""
    s = text.replace("\xa0", " ").replace("€", "").replace("EUR", "").strip()
    if not s or not re.fullmatch(r"[\d., ]+", s):
        raise ValueError(f"not a Dutch-formatted euro amount: {text!r}")
    if "," in s:
        whole, frac = s.rsplit(",", 1)
        whole = whole.replace(".", "").replace(" ", "")
        if not whole:
            whole = "0"
        return Decimal(f"{whole}.{frac}")
    return Decimal(s.replace(".", "").replace(" ", ""))


def _strip_tags(fragment: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", fragment).split())


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def _post(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None,
          *, timeout: int = 60, attempts: int = 4) -> tuple[int, bytes]:
    """POST with bounded exponential backoff. Returns (status, body)."""
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with _session().post(url, json=payload, headers=headers, timeout=timeout) as r:
                status = r.status_code
                if status >= 500 and attempt < attempts:
                    raise requests.HTTPError(f"{status} from {url}")
                r.raise_for_status()
                return status, r.content
        except Exception as exc:  # noqa: BLE001 - retried, then surfaced
            last = exc
            if attempt < attempts:
                time.sleep(min(2**attempt, 30))
    raise RuntimeError(f"fetch failed after {attempts} attempts: POST {url} :: {last}")


def _get(url: str, *, timeout: int = 60, attempts: int = 4) -> tuple[int, bytes]:
    """GET with bounded exponential backoff. Returns (status, body)."""
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with _session().get(url, timeout=timeout) as r:
                status = r.status_code
                if status >= 500 and attempt < attempts:
                    raise requests.HTTPError(f"{status} from {url}")
                r.raise_for_status()
                return status, r.content
        except Exception as exc:  # noqa: BLE001 - retried, then surfaced
            last = exc
            if attempt < attempts:
                time.sleep(min(2**attempt, 30))
    raise RuntimeError(f"fetch failed after {attempts} attempts: GET {url} :: {last}")


def _stamp() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _digest(body: bytes) -> tuple[str, int]:
    return hashlib.sha256(body).hexdigest(), len(body)


def _save(raw_dir: Path, name: str, body: bytes) -> str:
    path = raw_dir / "partijfinanciering" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return str(path)


# --------------------------------------------------------------------------
# 1. document index (GraphQL)
# --------------------------------------------------------------------------

def jaarverslagen(*, raw_dir: Path) -> Fetched:
    """The jaarverslagen document index. 92 rows expected, 2020-2024; PDFs are not downloaded."""
    status, body = _post(
        GRAPHQL_URL,
        {"query": JAARVERSLAGEN_QUERY},
        headers={"Content-Type": "application/json", "Origin": "https://www.partijfinanciering.nl"},
    )
    sha, n = _digest(body)
    fetched = Fetched(
        source="partijfinanciering:jaarverslagen",
        url=GRAPHQL_URL,
        params={"query": JAARVERSLAGEN_QUERY},
        retrieved_at=_stamp(),
        status=status,
        sha256=sha,
        n_bytes=n,
        raw_path=None,
        body=body,
        note="documents served as links to open.overheid.nl; PDFs deliberately not fetched",
    )
    _save(raw_dir, "jaarverslagen.json", body)
    return fetched


def parse_jaarverslagen(fetched: Fetched) -> list[dict[str, Any]]:
    """Documents out of the stored payload..partij is kept verbatim; key is lower(trim)."""
    rows = fetched.json()["data"]["jaarverslagen"]
    for r in rows:
        r["partij_key"] = (r["partij"] or "").strip().lower()
    return rows


# --------------------------------------------------------------------------
# 2. subsidies (SSR, two tables)
# --------------------------------------------------------------------------

def _tables(html: str) -> list[str]:
    return re.findall(r"<table\b.*?</table>", html, flags=re.S)


def _cell_text(cell: str) -> str:
    return _strip_tags(cell)


def _rows_of(table: str) -> list[str]:
    return re.findall(r"<tr\b.*?</tr>", table, flags=re.S)


def parse_subsidies(html: str) -> dict[str, Any]:
    """Two tables: [0] totals per year, [1] per party per year.

    Returns {"totals": [{jaar, bedrag_eur}], "parties": [{partij, partij_key,
    per_year: {jaar: (bedrag_eur|None, status)}}]}.
    """
    tables = _tables(html)
    if len(tables) != 2:
        raise ValueError(f"expected 2 tables on /dashboard/subsidies, found {len(tables)}; "
                         "page structure changed - re-probe before parsing")

    # --- totals table: header row is years, single value row beneath it
    tot_rows = _rows_of(tables[0])
    if len(tot_rows) != 2:
        raise ValueError(f"totals table: expected 2 rows, found {len(tot_rows)}")
    year_cells = re.findall(r"<th\b[^>]*>(.*?)</th>", tot_rows[0], flags=re.S)
    years = [int(_strip_tags(c)) for c in year_cells]
    value_cells = re.findall(r"<td\b[^>]*>(.*?)</td>", tot_rows[1], flags=re.S)
    if len(value_cells) != len(years):
        raise ValueError(f"totals table: {len(years)} header years vs {len(value_cells)} values")
    totals = []
    for year, cell in zip(years, value_cells):
        txt = _cell_text(cell).replace("\xa0", " ").strip()
        totals.append({"jaar": year,
                       "bedrag_eur": parse_eur(txt) if txt not in ("", "-") else None})

    # --- per-party table: header "Partij | 2022 | 2023 | 2024", one row per party
    party_rows = _rows_of(tables[1])
    header_cells = re.findall(r"<th\b[^>]*>(.*?)</th>", party_rows[0], flags=re.S)
    year_header = [int(_strip_tags(c)) for c in header_cells[1:]]
    parties = []
    for row in party_rows[1:]:
        cells = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row, flags=re.S)
        name = _cell_text(cells[0])
        per_year: dict[int, tuple[Decimal | None, str]] = {}
        for year, cell in zip(year_header, cells[1:]):
            txt = _cell_text(cell).replace("\xa0", " ").strip()
            if txt in ("", "-"):
                per_year[year] = (None, STATUS_NOT_ENTITLED)
            else:
                per_year[year] = (parse_eur(txt), STATUS_PRESENT)
        parties.append({"partij": name, "partij_key": name.strip().lower(),
                        "per_year": per_year})
    return {"totals": totals, "parties": parties}


def subsidies(*, raw_dir: Path) -> Fetched:
    """Fetch the SSR subsidies page and store the raw HTML."""
    status, body = _get(SUBSIDIES_URL)
    sha, n = _digest(body)
    stamp = _stamp()
    fetched = Fetched(
        source="partijfinanciering:subsidies",
        url=SUBSIDIES_URL,
        params={},
        retrieved_at=stamp,
        status=status,
        sha256=sha,
        n_bytes=n,
        raw_path=None,
        body=body,
        note="server-rendered; two tables (totals + per party)",
    )
    _save(raw_dir, "subsidies.html", body)
    return fetched


# --------------------------------------------------------------------------
# 3. giften (SSR, one card per party)
# --------------------------------------------------------------------------

def parse_giften(html: str, jaar: int) -> dict[str, Any]:
    """One page of gift cards plus the total card. Empty year -> total 0,00 and zero cards."""
    total_m = re.search(
        r'Totaal</span>.*?text-xl font-semibold[^>]*>\s*€\s*' + _MONEY, html, flags=re.S)
    if not total_m:
        raise ValueError(f"giften {jaar}: total card not found; page structure changed")
    page_total = parse_eur(total_m.group(1))
    cards = re.findall(
        r'<h2 class="mb-1 text-xl font-semibold">(.*?)</h2>\s*<p class="text-foreground">'
        r'Totaal ontvangen bijdragen\s*<br/>\s*<span class="text-lg font-bold text-foreground">'
        r'€\s*(?:<!--\s*-->)?' + _MONEY + r'</span>', html, flags=re.S)
    rows = []
    for name, amount_text in cards:
        amount = parse_eur(amount_text.replace("\xa0", " "))
        rows.append({"partij": _strip_tags(name), "partij_key": _strip_tags(name).strip().lower(),
                     "bedrag_eur": amount, "status": STATUS_PRESENT})
    if rows:
        card_sum = sum((r["bedrag_eur"] for r in rows), Decimal("0"))
        if card_sum != page_total:
            raise ValueError(
                f"giften {jaar}: sum of party cards {card_sum} != page total {page_total}")
    return {"totaal": page_total, "rows": rows}


def giften(jaar: int, *, raw_dir: Path) -> Fetched:
    """Fetch one gifts page. 2022-2024 carry parties; 2019-2021 and 2025 render empty (0 parties)."""
    status, body = _get(f"{GIFTEN_URL}/{jaar}")
    sha, n = _digest(body)
    stamp = _stamp()
    fetched = Fetched(
        source="partijfinanciering:giften",
        url=f"{GIFTEN_URL}/{jaar}",
        params={},
        retrieved_at=stamp,
        status=status,
        sha256=sha,
        n_bytes=n,
        raw_path=None,
        body=body,
        note="server-rendered cards + total card",
    )
    _save(raw_dir, f"giften-{jaar}.html", body)
    return fetched
