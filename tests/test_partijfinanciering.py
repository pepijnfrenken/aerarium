"""Tests over the partijfinanciering adapter.

Fixtures under tests/fixtures/ are verbatim extracts of the live pages and the GraphQL payload,
fetched 2026-11-20. No network at test time.

Run: ``.venv/bin/python -m pytest -q tests/``
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from aerarium.sources.partijfinanciering import (
    STATUS_NOT_ENTITLED,
    STATUS_NO_DATA,
    STATUS_PRESENT,
    parse_eur,
    parse_giften,
    parse_subsidies,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _subsidies_html() -> str:
    return (FIXTURES / "subsidies.html").read_text(encoding="utf-8")


def _giften_html(jaar: str) -> str:
    return (FIXTURES / f"giften_{jaar}.html").read_text(encoding="utf-8")


def _jaarverslagen_json() -> str:
    return (FIXTURES / "pf_jaarverslagen.json").read_text(encoding="utf-8")


# --- the amount parser -------------------------------------------------------

def test_dutch_amount_parser() -> None:
    assert parse_eur("€ 28.873.282") == Decimal("28873282")
    assert parse_eur("€ 567.307,6") == Decimal("567307.6")
    assert parse_eur("€ 8.933.589,90") == Decimal("8933589.90")
    assert parse_eur("0,00") == Decimal("0.00")
    with pytest.raises(ValueError):
        parse_eur("")


# --- the document index ------------------------------------------------------

def test_document_index_fixture_has_92_rows() -> None:
    import json

    rows = json.loads(_jaarverslagen_json())["data"]["jaarverslagen"]
    assert len(rows) == 92
    years = sorted({r["jaar"] for r in rows})
    assert years == [2020, 2021, 2022, 2023, 2024]
    per_year = {}
    for r in rows:
        per_year[r["jaar"]] = per_year.get(r["jaar"], 0) + 1
    assert per_year == {2020: 14, 2021: 20, 2022: 19, 2023: 20, 2024: 19}


def test_document_rows_carry_provenance_fields() -> None:
    rows = json.loads(_jaarverslagen_json())["data"]["jaarverslagen"]
    for r in rows:
        assert set(r) == {
            "partij", "jaar", "deel", "datum", "pages", "bestand_grootte_mb", "link",
        }
        assert r["link"].startswith((
            "https://open.overheid.nl/documenten/",
            "https://open.overheid.nl/details/",
            "https://www.rijksoverheid.nl/binaries/",
        ))


# --- the subsidies page ------------------------------------------------------

def test_subsidies_two_tables() -> None:
    st = parse_subsidies(_subsidies_html())
    assert {t["jaar"]: t["bedrag_eur"] for t in st["totals"]} == {
        2022: Decimal("28873282"),
        2023: Decimal("31477637"),
        2024: Decimal("29131718"),
    }
    names = [p["partij_key"] for p in st["parties"]]
    assert names == [
        "vvd", "d66", "cda", "sp", "pvda", "gl", "pvdd", "fvd", "cu", "sgp",
        "denk", "50plus", "opnl", "bij1", "ja21", "volt", "bvnl", "bbb", "nsc",
    ]
    vvd = st["parties"][0]
    assert vvd["per_year"][2022] == (Decimal("5162692"), STATUS_PRESENT)
    assert vvd["per_year"][2024] == (Decimal("4634145"), STATUS_PRESENT)
    bij1 = st["parties"][13]
    assert bij1["per_year"][2024] == (None, STATUS_NOT_ENTITLED)
    nsc = st["parties"][18]
    assert nsc["per_year"][2022] == (None, STATUS_NOT_ENTITLED)


# --- the gifts pages ---------------------------------------------------------

def test_giften_2024_total_and_parties() -> None:
    g = parse_giften(_giften_html("2024"), 2024)
    assert g["totaal"] == Decimal("8933589.90")
    assert len(g["rows"]) == 20
    names = sorted(r["partij_key"] for r in g["rows"])
    assert names == [
        "50plus", "bbb", "bij1", "bvnl", "cda", "cu", "d66", "denk", "fvd", "gl",
        "ja21", "nsc", "opnl", "pvda", "pvdd", "pvv", "sgp", "sp", "volt", "vvd",
    ]
    gl = [r for r in g["rows"] if r["partij_key"] == "gl"][0]
    assert gl["partij"] == "GL"
    assert gl["bedrag_eur"] == Decimal("2956497.23")
    assert gl["status"] == STATUS_PRESENT


def test_empty_years_are_no_data() -> None:
    for jaar in ("2019", "2020", "2021", "2025"):
        g = parse_giften(_giften_html(jaar), jaar)
        assert g["rows"] == []
        assert g["totaal"] == Decimal("0.00")


# --- the '-' cell rule -------------------------------------------------------

def test_dash_cells_are_null_not_zero() -> None:
    st = parse_subsidies(_subsidies_html())
    flat = {p["partij"]: p["per_year"] for p in st["parties"]}
    for partij in flat:
        for year, (amount, status) in flat[partij].items():
            if amount is None:
                assert status == STATUS_NOT_ENTITLED
            else:
                assert status == STATUS_PRESENT
                assert amount > 0
    with pytest.raises(ValueError):
        parse_eur("-")


# --- the store round trip ----------------------------------------------------

def _fake_fetch(source: str, body: bytes):
    import hashlib
    from datetime import datetime, timezone

    from aerarium.sources.rijksfinancien import Fetched

    return Fetched(
        source=source,
        url=f"https://example.invalid/{source}",
        params={},
        retrieved_at=datetime.now(timezone.utc).replace(microsecond=0),
        status=200,
        sha256=hashlib.sha256(body).hexdigest(),
        n_bytes=len(body),
        raw_path=None,
        body=body,
    )


def test_store_round_trip_idempotent_and_provenanced(tmp_path) -> None:
    from aerarium import store
    from aerarium.sources import partijfinanciering as pf

    conn = store.connect(tmp_path / "t.duckdb")
    docs = pf.parse_jaarverslagen(_fake_fetch(
        "partijfinanciering:jaarverslagen", _jaarverslagen_json().encode()))
    n1 = store.load_pf_documents(conn, _fake_fetch(
        "partijfinanciering:jaarverslagen", _jaarverslagen_json().encode()), docs)
    assert n1 == 92
    n2 = store.load_pf_documents(conn, _fake_fetch(
        "partijfinanciering:jaarverslagen", _jaarverslagen_json().encode()), docs)
    assert n2 == 92
    assert conn.execute("SELECT count(*) FROM pf_document").fetchone()[0] == 92
    assert conn.execute(
        "SELECT count(*) FROM pf_document d LEFT JOIN source_fetch f USING (fetch_id) "
        "WHERE f.fetch_id IS NULL"
    ).fetchone()[0] == 0

    # empty year: exactly one sentinel row, NULL amount, no-data-published
    sentinel = [{"partij": None, "partij_key": None, "bedrag_eur": None,
                 "status": STATUS_NO_DATA}]
    fetched = _fake_fetch("partijfinanciering:giften", b"")
    n = store.load_pf_gifts(conn, fetched, 2021, sentinel)
    assert n == 1
    n = store.load_pf_gifts(conn, fetched, 2021, sentinel)
    assert n == 1
    row = conn.execute(
        "SELECT partij, partij_key, bedrag_eur, status FROM pf_gift WHERE jaar=2021"
    ).fetchone()
    assert row == (None, None, None, STATUS_NO_DATA)
    assert conn.execute("SELECT count(*) FROM pf_gift").fetchone()[0] == 1
