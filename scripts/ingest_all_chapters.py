#!/usr/bin/env python3
"""Ingest every Rijksbegroting chapter, so the top-down chain can be followed for all ministries.

The first build loaded only chapters V and VII, because that is where party funding sits. The
government run needs the whole Rijksbegroting, so this walks every chapter identifier the API
serves, for every year, and records what came back per chapter-year.

Two facts about this source that decide the analysis downstream:

  * A chapter-year returns every phase the endpoint serves in one call. `fase` is OWB (the draft
    budget) or JV (the realised account). O1/O2 - the supplementary budgets - are NOT served;
    they return the same unfiltered set as XX, so a ceiling here is the draft ceiling only.
  * `instrument_of_uitsplitsing_apparaat_naam` carries 'Personele uitgaven' and 'Materiele
    uitgaven' as instruments, and `beleid_of_niet_beleid` marks policy vs apparatus. That is
    what makes 'how much is stuck paying people' answerable at all.

Rows are replaced per (year, chapter), so re-running is idempotent and a chapter that fails does
not disturb the others.
"""

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aerarium import sources  # noqa: E402
from aerarium.sources import rijksfinancien  # noqa: E402
from aerarium import store  # noqa: E402

# Every chapter identifier the API answered for in the probe. I, II, XI, XVIII, XIX and XX
# returned nothing in 2024; they are kept in the list because other years may serve them and a
# zero is a finding about coverage, not a reason to omit the attempt.
CHAPTERS = [
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX",
    "A", "B", "C", "D", "E", "F", "G", "H",
]
YEARS = list(range(2016, 2027))


def _connect_with_retry(path: pathlib.Path, tries: int = 15, wait_s: int = 20) -> "store.duckdb.DuckDBPyConnection | None":
    """DuckDB allows one read-write process per file. Lanes run Python kernels that may hold the
    lock for a while, so wait rather than fail, and never kill someone else's work to get it."""
    import time

    for attempt in range(1, tries + 1):
        try:
            return store.connect(path)
        except Exception as exc:  # noqa: BLE001
            if "lock" not in str(exc).lower() or attempt == tries:
                print(f"  connect failed ({str(exc)[:80]})", file=sys.stderr)
                return None
            print(f"  database locked, waiting {wait_s}s ({attempt}/{tries})", file=sys.stderr)
            time.sleep(wait_s)
    return None


def main() -> int:
    raw_dir = rijksfinancien.default_raw_dir()
    target = ROOT / "data" / "aerarium.duckdb"
    conn = _connect_with_retry(target)
    if conn is None:
        # Fall back to a staging file rather than lose the ingest. Every row is replaced per
        # (year, chapter), so merging is a plain INSERT ... SELECT once the lock clears.
        target = ROOT / "data" / "budget_all.duckdb"
        print(f"  main database unavailable; staging into {target.name}", file=sys.stderr)
        conn = store.connect(target)
    total = 0
    matrix: dict[str, dict[int, int]] = {}

    for chapter in CHAPTERS:
        matrix[chapter] = {}
        for year in YEARS:
            try:
                fetched = rijksfinancien.budget(year, chapter, raw_dir=raw_dir)
                rows = fetched.json()
            except Exception as exc:  # noqa: BLE001
                print(f"  {chapter} {year}: fetch failed ({str(exc)[:60]})", file=sys.stderr)
                matrix[chapter][year] = -1
                continue
            if not isinstance(rows, list) or not rows:
                matrix[chapter][year] = 0
                continue
            fetched.extra["licence"] = rijksfinancien.LICENCE
            n = store.load_budget(conn, fetched, rows, chapter=chapter)
            matrix[chapter][year] = n
            total += n
        got = sum(v for v in matrix[chapter].values() if v > 0)
        name = ""
        if got:
            row = conn.execute(
                "select hoofdstuk_naam from budget_line where hoofdstuk_nummer=? and hoofdstuk_naam is not null limit 1",
                [chapter],
            ).fetchone()
            name = row[0] if row else ""
        print(f"  {chapter:<4}{name[:44]:<46}{got:>4} years  {sum(matrix[chapter].values()):>7} rows")

    conn.close()
    print(f"\nloaded {total} budget rows across {len(CHAPTERS)} chapter identifiers")

    blanks = [c for c, m in matrix.items() if not any(v > 0 for v in m.values())]
    if blanks:
        print(f"no rows served for: {', '.join(blanks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
