"""The Tabularium: one DuckDB store, provenance on every row.

Design rules, enforced here rather than in convention:

* every loaded row carries the `fetch_id` of the response it came from, and `fetch` carries url, params,
  retrieval timestamp, sha256 and byte count;
* amounts are stored in the unit the source printed (`bedrag_k` = EUR thousand) and never silently
  converted between the budget table and the register, which use different units in the same API family;
* loads are idempotent: re-ingesting a year replaces that year's rows rather than appending duplicates.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import duckdb

from .sources.rijksfinancien import Fetched

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_fetch (
    fetch_id      VARCHAR PRIMARY KEY,
    source        VARCHAR NOT NULL,
    url           VARCHAR NOT NULL,
    params        VARCHAR,
    retrieved_at  TIMESTAMP NOT NULL,
    http_status   INTEGER,
    n_bytes       BIGINT,
    sha256        VARCHAR,
    licence       VARCHAR,
    raw_path      VARCHAR,
    note          VARCHAR
);

CREATE TABLE IF NOT EXISTS budget_line (
    fetch_id                 VARCHAR NOT NULL,
    jaar                     INTEGER NOT NULL,
    fase                     VARCHAR NOT NULL,
    vuo                      VARCHAR,
    index_id                 VARCHAR,
    hoofdstuk_nummer         VARCHAR,
    hoofdstuk_naam           VARCHAR,
    artikel_nummer           VARCHAR,
    artikel_naam             VARCHAR,
    artikelonderdeel_nummer  VARCHAR,
    artikelonderdeel_naam    VARCHAR,
    instrument_nummer        VARCHAR,
    instrument_naam          VARCHAR,
    regeling_nummer          VARCHAR,
    regeling_naam            VARCHAR,
    bedrag_k                 BIGINT,
    verantwoordelijk_minister VARCHAR,
    beleid_of_niet_beleid    VARCHAR,
    rbv_model                VARCHAR
);

CREATE TABLE IF NOT EXISTS recipient_line (
    fetch_id          VARCHAR NOT NULL,
    jaar              INTEGER NOT NULL,
    hoofdstuk         VARCHAR,
    hoofdstuk_naam    VARCHAR,
    ris_ibos          VARCHAR,
    artikel           VARCHAR,
    artikelonderdeel  VARCHAR,
    instrument        VARCHAR,
    detail            VARCHAR,
    regeling          VARCHAR,
    ontvanger         VARCHAR,
    ontvanger_key     VARCHAR,
    bedrag_k          BIGINT,
    kvk               VARCHAR,
    rechtsvorm        VARCHAR,
    plaats            VARCHAR,
    anonymised        BOOLEAN
);

CREATE TABLE IF NOT EXISTS adjudication (
    adjudication_id  VARCHAR PRIMARY KEY,
    subject          VARCHAR NOT NULL,
    decision         VARCHAR NOT NULL,
    field_matched    VARCHAR,
    evidence         VARCHAR,
    decided_by       VARCHAR,
    decided_at       TIMESTAMP
);
"""

RECIPIENT_COLUMNS = {
    "jaar": "VARCHAR",
    "hoofdstuk": "VARCHAR",
    "hoofdstuk_naam": "VARCHAR",
    "ris_ibos": "VARCHAR",
    "artikel": "VARCHAR",
    "artikelonderdeel": "VARCHAR",
    "instrument": "VARCHAR",
    "detail": "VARCHAR",
    "regeling": "VARCHAR",
    "ontvanger": "VARCHAR",
    "bedrag": "VARCHAR",
    "kvk": "VARCHAR",
    "rechtsvorm": "VARCHAR",
    "plaats": "VARCHAR",
}


def connect(path: Path | str) -> duckdb.DuckDBPyConnection:
    if isinstance(path, (str, Path)) and str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(path))
    conn.execute(SCHEMA)
    return conn


def log_fetch(conn: duckdb.DuckDBPyConnection, fetched: Fetched, licence: str) -> str:
    fetch_id = f"{fetched.source}#{fetched.sha256[:16]}"
    conn.execute(
        """
        INSERT INTO source_fetch VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT (fetch_id) DO NOTHING
        """,
        [
            fetch_id,
            fetched.source,
            fetched.url,
            repr(sorted(fetched.params.items())) if fetched.params else None,
            fetched.retrieved_at,
            fetched.status,
            fetched.n_bytes,
            fetched.sha256,
            licence,
            fetched.raw_path,
            fetched.note,
        ],
    )
    return fetch_id


def load_budget(
    conn: duckdb.DuckDBPyConnection,
    fetched: Fetched,
    rows: Iterable[dict[str, Any]],
    *,
    chapter: str,
) -> int:
    """Replace the stored rows for this chapter across every year present in the payload."""
    rows = list(rows)
    years = sorted({int(r["jaar"]) for r in rows if r.get("jaar") is not None})
    fetch_id = log_fetch(conn, fetched, licence=fetched.extra.get("licence", ""))
    for year in years:
        conn.execute("DELETE FROM budget_line WHERE jaar=? AND hoofdstuk_nummer=?", [year, chapter])
    payload = [
        [
            fetch_id,
            int(r["jaar"]),
            r.get("fase"),
            r.get("vuo"),
            r.get("index"),
            r.get("hoofdstuk_nummer"),
            r.get("hoofdstuk_naam"),
            r.get("artikel_nummer"),
            r.get("artikel_naam"),
            r.get("artikelonderdeel_nummer"),
            r.get("artikelonderdeel_naam"),
            r.get("instrument_of_uitsplitsing_apparaat_nummer"),
            r.get("instrument_of_uitsplitsing_apparaat_naam"),
            r.get("regeling_detailniveau_nummer"),
            r.get("regeling_detailniveau_naam"),
            int(r["bedrag"]) if r.get("bedrag") is not None else None,
            r.get("verantwoordelijk_minister"),
            r.get("beleid_of_niet_beleid"),
            r.get("rbv_model"),
        ]
        for r in rows
    ]
    conn.executemany(
        "INSERT INTO budget_line VALUES (" + ",".join(["?"] * 19) + ")", payload
    )
    return len(payload)


def load_recipients(conn: duckdb.DuckDBPyConnection, fetched: Fetched, csv_path: Path) -> int:
    """Load the row-level register. Column order is pinned, not inferred from the header."""
    fetch_id = log_fetch(conn, fetched, licence="CC-0 / publiek domein (Ministerie van Financien)")
    conn.execute("DELETE FROM recipient_line")
    cols = ",".join(f"'{k}': '{v}'" for k, v in RECIPIENT_COLUMNS.items())
    conn.execute(
        f"""
        INSERT INTO recipient_line
        SELECT
            ?,
            TRY_CAST(jaar AS INTEGER),
            hoofdstuk, hoofdstuk_naam, ris_ibos, artikel, artikelonderdeel,
            instrument, detail, regeling,
            ontvanger,
            lower(trim(ontvanger)),
            TRY_CAST(ROUND(TRY_CAST(
                replace(replace(trim(bedrag), '.', ''), ',', '.') AS DOUBLE)) AS BIGINT),
            kvk, rechtsvorm, plaats,
            regexp_matches(lower(trim(coalesce(ontvanger, ''))), '^geanonimiseerde ontvanger')
        FROM read_csv(?, delim=';', header=false, skip=1, all_varchar=true,
                      quote='"', escape='"', columns={{{cols}}})
        """,
        [fetch_id, str(csv_path)],
    )
    n = conn.execute("SELECT count(*) FROM recipient_line").fetchone()[0]
    bad = conn.execute(
        "SELECT count(*) FROM recipient_line WHERE bedrag_k IS NULL"
    ).fetchone()[0]
    if bad:
        raise ValueError(f"{bad} recipient rows have an unparseable amount; refusing partial load")
    return int(n)


def adjudicate(
    conn: duckdb.DuckDBPyConnection,
    *,
    adjudication_id: str,
    subject: str,
    decision: str,
    field_matched: str,
    evidence: str,
    decided_by: str = "quaestor",
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO adjudication VALUES (?,?,?,?,?,?,?)",
        [
            adjudication_id,
            subject,
            decision,
            field_matched,
            evidence,
            decided_by,
            datetime.now().replace(microsecond=0),
        ],
    )


def provenance_of(conn: duckdb.DuckDBPyConnection, fetch_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT source, url, params, retrieved_at, sha256, licence FROM source_fetch WHERE fetch_id=?",
        [fetch_id],
    ).fetchone()
    keys = ("source", "url", "params", "retrieved_at", "sha256", "licence")
    return dict(zip(keys, row)) if row else {}
