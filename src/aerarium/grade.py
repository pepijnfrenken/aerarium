"""Chain grading: how far down the chain of custody a euro survives, and where it breaks.

The chain, in order, from docs/GRADING.md:

  r1  the begroting chapter and the beleidsartikel that carries the money
  r2  the article's ceiling and every amendment to it (O1, O2 suppletoire wetten)
  r3  the instrument (a subsidy scheme, a regeling, an opdracht, a bijdrage)
  r4  the recipient, where recipients are published at all
  r5  the realisation in the Financieel Jaarverslag
  r6  a Rekenkamer finding on that line

Two rules govern this file.

*A rung is not a score.* `reach` counts documented rungs; `breaks` names the ones that are absent,
aggregated or unavailable. A ceiling is not a payment and an aggregate is not a flow, so `ceiling_k`,
`realised_k`, `named_k` and `anon_k` are never added together anywhere here.

*r4 is measured in euros, not in row labels.* A year where 20 parties are named and the other 87% of the
money sits in no row at all is `partial`, not `named`. Label-based grading flatters the disclosure, which is
precisely the failure this repository is built to avoid.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import duckdb

from . import schemes

# Status vocabulary. Keep these exact strings: the CSV is the artifact and prose quotes them.
DOCUMENTED = "documented"
DOCUMENTED_ZERO = "documented-zero"
NAMED = "named"
PARTIAL = "partial"
AGGREGATE_ONLY = "aggregate-only"
ABSENT = "absent"
NOT_PUBLISHED = "not-published"
NOT_SEPARABLE = "not-separable"
UNAVAILABLE = "unavailable-in-source"
NOT_PROBED = "not-probed"

REACHED = {DOCUMENTED, DOCUMENTED_ZERO, NAMED}
NAMED_COVERAGE_FLOOR = 0.999


@dataclass
class Row:
    jaar: int
    family: str
    label: str
    group: str
    instruments: str
    budget_names: str
    register_names: str
    ceiling_k: int | None
    owb_rows: int
    realised_k: int | None
    jv_rows: int
    named_rows: int
    named_k: int | None
    anon_rows: int
    anon_k: int | None
    unreconciled_k: int | None
    named_coverage: float | None
    disclosed_coverage: float | None
    r1: str
    r2: str
    r3: str
    r4: str
    r5: str
    r6: str
    reach: int
    breaks: str
    recipient_source: str
    notes: str

    def as_csv(self) -> dict[str, Any]:
        d = asdict(self)
        for key in ("named_coverage", "disclosed_coverage"):
            if d[key] is not None:
                d[key] = f"{d[key]:.4f}"
        return d


def _scheme_map(conn: duckdb.DuckDBPyConnection) -> None:
    """Temp table: every scheme name actually seen in either source -> its canonical family."""
    names: set[str] = set()
    for (n,) in conn.execute(
        "SELECT DISTINCT regeling_naam FROM budget_line WHERE regeling_naam IS NOT NULL"
    ).fetchall():
        names.add(n)
    for (n,) in conn.execute(
        "SELECT DISTINCT regeling FROM recipient_line WHERE regeling IS NOT NULL"
    ).fetchall():
        names.add(n)
    conn.execute("CREATE OR REPLACE TEMP TABLE scheme_map (nama VARCHAR, family VARCHAR)")
    conn.executemany(
        "INSERT INTO scheme_map VALUES (?,?)",
        [(n, schemes.classify(n)) for n in sorted(names)],
    )


def phase_availability(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    return {
        f: int(n)
        for f, n in conn.execute(
            "SELECT fase, count(*) FROM budget_line GROUP BY 1 ORDER BY 1"
        ).fetchall()
    }


def unmapped_schemes(conn: duckdb.DuckDBPyConnection, *, min_k: int = 0) -> list[tuple[str, int]]:
    """Names this table does not classify, inside the sub-articles that carry a mapped party scheme.

    Unclassified names are a gap in schemes.py, not an absence of spending, so they are reported rather
    than dropped. Scope is the sub-article: chapter VII carries 27bn of housing allowance and chapter V
    carries an arms-length aid programme, and neither belongs in a party ledger by accident.
    """
    _scheme_map(conn)
    return [
        (nama, int(total))
        for nama, total in conn.execute(
            """
            WITH party_ao AS (
                SELECT DISTINCT b.artikelonderdeel_naam AS ao
                FROM budget_line b JOIN scheme_map m ON b.regeling_naam = m.nama
                WHERE m.family <> ?
            )
            SELECT b.regeling_naam, sum(b.bedrag_k)
            FROM budget_line b JOIN scheme_map m ON b.regeling_naam = m.nama
            WHERE m.family = ? AND b.vuo='U' AND b.fase='OWB'
              AND b.artikelonderdeel_naam IN (SELECT ao FROM party_ao)
            GROUP BY 1 HAVING sum(b.bedrag_k) >= ?
            ORDER BY 2 DESC
            """,
            [schemes.UNMAPPED, schemes.UNMAPPED, min_k],
        ).fetchall()
    ]


def _names(conn: duckdb.DuckDBPyConnection, table: str, column: str, family: str, year: int) -> str:
    row = conn.execute(
        f"""
        SELECT string_agg(DISTINCT {column}, '|' ORDER BY {column})
        FROM {table} t JOIN scheme_map m ON t.{column} = m.nama
        WHERE m.family = ? AND t.jaar = ?
        """,
        [family, year],
    ).fetchone()
    return (row[0] if row and row[0] else "") or ""


def _r4(named_rows: int, anon_rows: int, named_k: int, realised_k: int | None, in_coverage: bool) -> str:
    if not in_coverage:
        return NOT_PUBLISHED
    if named_rows == 0 and anon_rows == 0:
        return ABSENT
    if realised_k:
        coverage = named_k / realised_k
        if anon_rows == 0 and coverage >= NAMED_COVERAGE_FLOOR:
            return NAMED
        return PARTIAL if named_k > 0 else AGGREGATE_ONLY
    # No realisation to compare against: fall back to what the labels say, and say so in the grade.
    if named_rows and not anon_rows:
        return NAMED
    if named_rows and anon_rows:
        return PARTIAL
    return AGGREGATE_ONLY


def series(conn: duckdb.DuckDBPyConnection) -> list[Row]:
    _scheme_map(conn)
    phases = phase_availability(conn)
    amendments_served = phases.get("O1", 0) + phases.get("O2", 0) > 0

    cov = conn.execute("SELECT min(jaar), max(jaar) FROM recipient_line").fetchone()
    min_rec = int(cov[0]) if cov and cov[0] is not None else None
    max_rec = int(cov[1]) if cov and cov[1] is not None else None

    out: list[Row] = []
    for family in schemes.FAMILIES:
        spec = schemes.family_spec(family)
        for year in spec.years(conn):
            b = conn.execute(
                """
                SELECT fase, sum(bedrag_k), count(*)
                FROM budget_line t JOIN scheme_map m ON t.regeling_naam = m.nama
                WHERE m.family=? AND t.jaar=? AND t.vuo='U'
                GROUP BY 1
                """,
                [family, year],
            ).fetchall()
            by_phase = {f: (int(s or 0), int(n)) for f, s, n in b}
            ceiling_k, owb_rows = by_phase.get("OWB", (None, 0))
            realised_k, jv_rows = by_phase.get("JV", (None, 0))

            r = conn.execute(
                """
                SELECT
                  coalesce(sum(CASE WHEN NOT anonymised THEN 1 END), 0),
                  coalesce(sum(CASE WHEN NOT anonymised THEN bedrag_k END), 0),
                  coalesce(sum(CASE WHEN anonymised THEN 1 END), 0),
                  coalesce(sum(CASE WHEN anonymised THEN bedrag_k END), 0)
                FROM recipient_line t JOIN scheme_map m ON t.regeling = m.nama
                WHERE m.family=? AND t.jaar=?
                """,
                [family, year],
            ).fetchone()
            named_rows, named_k, anon_rows, anon_k = (int(x or 0) for x in r)

            instruments = conn.execute(
                """
                SELECT string_agg(DISTINCT instrument_naam, '|' ORDER BY instrument_naam)
                FROM budget_line t JOIN scheme_map m ON t.regeling_naam = m.nama
                WHERE m.family=? AND t.jaar=? AND t.fase='OWB' AND t.vuo='U'
                      AND instrument_naam IS NOT NULL AND instrument_naam <> ''
                """,
                [family, year],
            ).fetchone()[0] or ""

            budget_names = _names(conn, "budget_line", "regeling_naam", family, year)
            register_names = _names(conn, "recipient_line", "regeling", family, year)

            notes: list[str] = []
            if len({n for n in budget_names.split("|") if n}) > 1 or (
                len({n for n in register_names.split("|") if n}) > 1
            ):
                notes.append("scheme renamed in this year; see budget_names/register_names")
            if budget_names and register_names and budget_names.lower() != register_names.lower():
                notes.append(
                    "budget and register name this line differently; same money, different label"
                )

            in_coverage = (
                min_rec is not None and max_rec is not None and min_rec <= year <= max_rec
            )

            if owb_rows:
                r1 = DOCUMENTED
                r3 = DOCUMENTED if instruments else ABSENT
            elif spec.register_only:
                r1 = NOT_SEPARABLE
                r3 = NOT_SEPARABLE
                notes.append(spec.note)
            else:
                r1 = ABSENT
                r3 = ABSENT

            r2 = DOCUMENTED if amendments_served else UNAVAILABLE
            r4 = _r4(named_rows, anon_rows, named_k, realised_k, in_coverage)

            if jv_rows:
                r5 = DOCUMENTED_ZERO if (realised_k or 0) == 0 else DOCUMENTED
            else:
                r5 = ABSENT

            r6 = NOT_PROBED


            # No register rows at all is not a disclosure of zero named money: it means the register publishes
            # nothing on this line, so the named share cannot be computed. Emitting 0 there stated "0% of the
            # money is named", which is a measurement the source does not support. Zeros survive only where
            # the register does publish on the line, including the genuine case of rows that are all anonymised.
            no_register_rows = named_rows == 0 and anon_rows == 0
            if no_register_rows:
                named_k = None
                anon_k = None
            elif named_rows == 0 or anon_rows == 0:
                # The register does publish on this line, so 0 is a real figure for the component that has no
                # rows - but a reader cannot tell a measured zero from an absent component by the number alone.
                # The note carries which side is empty, so the CSV never looks like it measured what it lacks.
                empty = "named" if named_rows == 0 else "anonymised"
                notes.append(f"no {empty} recipient rows published in this year; that component is 0 by absence, "
                             f"not by measurement")

            unreconciled = None
            if realised_k is not None and r4 not in (NOT_PUBLISHED, ABSENT):
                unreconciled = int(realised_k) - named_k - anon_k

            named_cov = (named_k / realised_k) if (realised_k and named_k is not None) else None
            disclosed_cov = ((named_k + anon_k) / realised_k) if (realised_k and named_k is not None) else None

            rungs = [r1, r2, r3, r4, r5, r6]
            reach = sum(1 for s in rungs if s in REACHED)
            breaks = ";".join(
                f"r{i}:{s}" for i, s in enumerate(rungs, start=1) if s not in REACHED and s != UNAVAILABLE
            )

            if ceiling_k is None and realised_k is None and named_rows == 0 and anon_rows == 0:
                continue

            out.append(
                Row(
                    jaar=year,
                    family=family,
                    label=spec.label,
                    group=spec.group,
                    instruments=instruments,
                    budget_names=budget_names,
                    register_names=register_names,
                    ceiling_k=ceiling_k,
                    owb_rows=owb_rows,
                    realised_k=realised_k,
                    jv_rows=jv_rows,
                    named_rows=named_rows,
                    named_k=named_k,
                    anon_rows=anon_rows,
                    anon_k=anon_k,
                    unreconciled_k=unreconciled,
                    named_coverage=named_cov,
                    disclosed_coverage=disclosed_cov,
                    r1=r1,
                    r2=r2,
                    r3=r3,
                    r4=r4,
                    r5=r5,
                    r6=r6,
                    reach=reach,
                    breaks=breaks,
                    recipient_source=(
                        "row-level register (KvK carried)" if in_coverage else "not published at row level"
                    ),
                    notes="; ".join(notes),
                )
            )
    return out


def write_csv(rows: list[Row], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("no rows to write")
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].as_csv().keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_csv())
    return path


def summary(rows: list[Row]) -> str:
    """A plain-text ledger, for the terminal and for pasting into a memo."""
    lines: list[str] = []
    head = (
        f"{'year':<5}{'family':<38}{'ceiling':>10}{'realised':>10}"
        f"{'named':>10}{'anon':>10}{'unrec':>10}  {'r4':<18}reach"
    )
    lines.append(head)
    lines.append("-" * len(head))

    def f(v: int | None) -> str:
        return "" if v is None else f"{v:,}"

    for row in rows:
        lines.append(
            f"{row.jaar:<5}{row.family[:37]:<38}{f(row.ceiling_k):>10}{f(row.realised_k):>10}"
            f"{f(row.named_k):>10}{f(row.anon_k):>10}{f(row.unreconciled_k):>10}  "
            f"{row.r4:<18}{row.reach}"
        )
    return "\n".join(lines)
