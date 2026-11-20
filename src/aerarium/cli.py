"""aerarium CLI. `aer` is the binary.

    aer sync                 fetch, load, grade, write the artifact (the whole pipeline)
    aer ingest-budget        just the appropriation spine for a chapter
    aer ingest-recipients    just the row-level recipient register
    aer ingest-partijfinanciering   documents, subsidies, giften from partijfinanciering.nl
    aer validate-party       integrity checks over the party-financing tables
    aer grade                grade from what is already stored
    aer validate             integrity checks that must pass before a number is quoted
    aer probe-vintage        is the row-level register refreshed, or stale?
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from . import grade, schemes, store
from .sources import partijfinanciering as pf
from .sources import rijksfinancien
from .sources.partijfinanciering import STATUS_NO_DATA, parse_giften, parse_subsidies

DEFAULT_DB = Path("data/aerarium.duckdb")
DEFAULT_OUT = Path("out")


def _eur(amount: float | Decimal | None) -> str:
    """Dutch formatting: 28873282.5 -> '28.873.282,50'. None -> 'geen bedrag'."""
    if amount is None:
        return "geen bedrag"
    q = Decimal(str(amount)).quantize(Decimal("0.01"))
    whole, frac = divmod(q, 1)
    whole_s = f"{int(whole):,}".replace(",", ".")
    return f"{whole_s},{str(frac)[2:]}"

LEDGER_HEADER = (
    "AERARIUM / Tabularium — CC-0 source: rijksfinancien.nl (Ministerie van Financien). "
    "Amounts in EUR thousand unless stated. A ceiling is not a payment."
)


def _years(spec: str) -> list[int]:
    """'2016-2026' or '2019,2021' -> [2016..2026]. Inclusive both ends."""
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return sorted(set(out))


def _raw_dir() -> Path:
    return rijksfinancien.default_raw_dir()


def cmd_ingest_budget(args) -> int:
    conn = store.connect(args.db)
    raw = _raw_dir() / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = 0
    for year in _years(args.years):
        fetched = rijksfinancien.budget(year, args.chapter, raw_dir=raw)
        try:
            rows = fetched.json()
        except Exception as exc:  # noqa: BLE001
            print(f"  {year}: unreadable payload ({exc})", file=sys.stderr)
            continue
        if not isinstance(rows, list) or not rows:
            print(f"  {year}: no rows returned")
            continue
        fetched.extra["licence"] = rijksfinancien.LICENCE
        n = store.load_budget(conn, fetched, rows, chapter=args.chapter)
        total += n
        phases = sorted({r.get("fase") for r in rows})
        print(f"  {year}: {n} rows, phases {phases}")
    print(f"loaded {total} budget rows for chapter {args.chapter}")
    return 0


def cmd_ingest_recipients(args) -> int:
    conn = store.connect(args.db)
    raw = _raw_dir() / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fetched = rijksfinancien.recipients_csv(raw_dir=raw, refresh=args.refresh)
    path = Path(fetched.raw_path or "")
    if not path.exists():
        print("no register file on disk", file=sys.stderr)
        return 1
    n = store.load_recipients(conn, fetched, path)
    years = conn.execute("SELECT min(jaar), max(jaar) FROM recipient_line").fetchone()
    print(f"loaded {n} recipient rows, years {years[0]}-{years[1]}, file {path.name}")
    return 0


def cmd_ingest_partijfinanciering(args) -> int:
    conn = store.connect(args.db)
    raw = _raw_dir() / datetime.now(timezone.utc).strftime("%Y-%m-%d")

    fetched = pf.jaarverslagen(raw_dir=raw)
    documents = pf.parse_jaarverslagen(fetched)
    n_docs = store.load_pf_documents(conn, fetched, documents)
    by_year: dict[int, int] = {}
    for r in documents:
        by_year[int(r["jaar"])] = by_year.get(int(r["jaar"]), 0) + 1
    print(f"documents: {n_docs}")
    for year in sorted(by_year):
        print(f"  {year}: {by_year[year]} documents")

    fetched = pf.subsidies(raw_dir=raw)
    parsed = parse_subsidies(fetched.body.decode("utf-8"))
    n_totals = store.load_pf_subsidy_totals(conn, fetched, parsed["totals"])
    n_subsidies = store.load_pf_subsidies(conn, fetched, parsed["parties"])
    print(f"subsidies: {n_totals} published totals, {n_subsidies} party rows")
    for t in parsed["totals"]:
        print(f"  {t['jaar']}: total EUR {_eur(t['bedrag_eur'])}")

    n_gift_rows = 0
    empty_years = 0
    for jaar in _years(args.giften_years):
        fetched = pf.giften(jaar, raw_dir=raw)
        parsed_g = parse_giften(fetched.body.decode("utf-8"), jaar)
        rows = parsed_g["rows"]
        if rows:
            n_gift_rows += store.load_pf_gifts(conn, fetched, jaar, rows)
            print(f"giften {jaar}: {len(rows)} parties, total EUR {_eur(parsed_g['totaal'])}")
        else:
            empty_years += 1
            n_gift_rows += store.load_pf_gifts(
                conn, fetched, jaar,
                [{"partij": None, "partij_key": None, "bedrag_eur": None,
                  "status": STATUS_NO_DATA}])
            print(f"giften {jaar}: page renders, zero parties -> no-data-published")
    print(f"giften: {n_gift_rows} rows, {empty_years} empty year(s)")
    return 0


def cmd_validate_party(args) -> int:
    conn = store.connect(args.db)
    problems = 0

    docs = conn.execute("SELECT count(*) FROM pf_document").fetchone()[0]
    years = conn.execute("SELECT min(jaar), max(jaar) FROM pf_document").fetchone()
    print(f"documents: {docs} (years {years[0]}-{years[1]})")
    if docs != 92:
        problems += 1
        print(f"  FAIL expected 92 documents, found {docs}")
    parties_per_year = conn.execute(
        "SELECT jaar, count(DISTINCT partij) FROM pf_document GROUP BY jaar ORDER BY jaar"
    ).fetchall()
    for year, n in parties_per_year:
        print(f"  {year}: {n} parties with a jaarverslag")

    print("subsidy totals per year, against the sum of the per-party rows:")
    subsidy_rows = conn.execute(
        """
        SELECT t.jaar, t.bedrag_eur,
               SUM(s.bedrag_eur) AS party_sum, COUNT(s.partij) AS n_parties
        FROM pf_subsidy_total t LEFT JOIN pf_subsidy s ON s.jaar = t.jaar
        GROUP BY t.jaar, t.bedrag_eur ORDER BY t.jaar
        """
    ).fetchall()
    for year, total, party_sum, n_parties in subsidy_rows:
        if total is None:
            print(f"  {year}: published total NULL, {n_parties} party rows")
            continue
        party_sum = party_sum if party_sum is not None else Decimal("0")
        diff = total - party_sum
        print(f"  {year}: total EUR {_eur(total)}, {n_parties} parties sum to "
              f"EUR {_eur(party_sum)}, difference {diff:+} euro")
        if n_parties == 0:
            problems += 1
            print(f"    FAIL no party rows for {year}")

    print("gift totals per year:")
    gift_rows = conn.execute(
        """
        SELECT jaar,
               SUM(bedrag_eur) AS total,
               COUNT(partij) AS n_parties,
               count(*) FILTER (WHERE status = 'no-data-published') AS n_nodata
        FROM pf_gift GROUP BY jaar ORDER BY jaar
        """
    ).fetchall()
    no_data_years = 0
    for year, total, n_parties, n_nodata in gift_rows:
        if n_nodata:
            no_data_years += 1
            print(f"  {year}: no-data-published (page rendered, zero parties)")
        else:
            print(f"  {year}: {n_parties} parties, sum EUR {_eur(total)}")
    print(f"years stored as no-data-published: {no_data_years}")

    nofetch = conn.execute(
        """
        SELECT (SELECT count(*) FROM pf_document d LEFT JOIN source_fetch f USING (fetch_id) WHERE f.fetch_id IS NULL)
             + (SELECT count(*) FROM pf_subsidy_total t LEFT JOIN source_fetch f USING (fetch_id) WHERE f.fetch_id IS NULL)
             + (SELECT count(*) FROM pf_subsidy s LEFT JOIN source_fetch f USING (fetch_id) WHERE f.fetch_id IS NULL)
             + (SELECT count(*) FROM pf_gift g LEFT JOIN source_fetch f USING (fetch_id) WHERE f.fetch_id IS NULL)
        """
    ).fetchone()[0]
    if nofetch:
        problems += 1
        print(f"FAIL {nofetch} party-financing rows without a provenance record")

    zero_leak = conn.execute(
        "SELECT count(*) FROM pf_gift WHERE status = 'no-data-published' AND bedrag_eur IS NOT NULL"
    ).fetchone()[0] + conn.execute(
        "SELECT count(*) FROM pf_subsidy WHERE status = 'not-entitled-or-not-paid' "
        "AND bedrag_eur IS NOT NULL"
    ).fetchone()[0]
    if zero_leak:
        problems += 1
        print(f"FAIL {zero_leak} rows carry an amount despite a null-ish status")

    print("validate-party:", "OK" if problems == 0 else f"{problems} problem(s)")
    return 0 if problems == 0 else 1


def cmd_grade(args) -> int:
    conn = store.connect(args.db)
    rows = grade.series(conn)
    if not rows:
        print("nothing to grade; run `aer ingest-budget` first", file=sys.stderr)
        return 1
    print(LEDGER_HEADER)
    print()
    print(grade.summary(rows))
    out = Path(args.out) / "party-line-disclosure.csv"
    grade.write_csv(rows, out)
    print()
    print(f"wrote {out}")
    unmapped = grade.unmapped_schemes(conn, min_k=1)
    if unmapped:
        print("\nUNMAPPED schemes in the party neighbourhood (add to schemes.py):")
        for name, total in unmapped[:20]:
            print(f"  {total:>12,}k  {name}")
    return 0


def cmd_validate(args) -> int:
    conn = store.connect(args.db)
    problems = 0
    phases = grade.phase_availability(conn)
    print("phases present in budget_line:", phases or "none")
    if phases.get("O1", 0) + phases.get("O2", 0) == 0:
        print("  r2: no O1/O2 rows stored — suppletoire wetten are not served by this endpoint")
    bad = conn.execute(
        "SELECT count(*) FROM recipient_line WHERE bedrag_k IS NULL"
    ).fetchone()[0]
    if bad:
        problems += 1
        print(f"  FAIL {bad} recipient rows with unparseable amount")
    dupes = conn.execute(
        """
        SELECT count(*) FROM (
          SELECT jaar, hoofdstuk, artikel, artikelonderdeel, instrument, detail, regeling,
                 ontvanger, bedrag_k, ris_ibos
          FROM recipient_line
          GROUP BY ALL HAVING count(*) > 1
        )
        """
    ).fetchone()[0]
    print(f"  fully identical recipient rows (incl. ris_ibos): {dupes}")
    kvk = conn.execute(
        """
        SELECT count(*) FILTER (WHERE anonymised) AS anon,
               count(*) FILTER (WHERE NOT anonymised AND kvk IS NOT NULL AND kvk <> '') AS with_kvk,
               count(*) FILTER (WHERE NOT anonymised) AS named
        FROM recipient_line
        """
    ).fetchone()
    print(f"  recipient rows: {kvk[0]:,} anonymised, {kvk[2]:,} named, {kvk[1]:,} of the named carry a KvK")
    nofetch = conn.execute(
        "SELECT count(*) FROM budget_line b LEFT JOIN source_fetch f USING (fetch_id) WHERE f.fetch_id IS NULL"
    ).fetchone()[0]
    if nofetch:
        problems += 1
        print(f"  FAIL {nofetch} budget rows without a provenance record")
    print("validate:", "OK" if problems == 0 else f"{problems} problem(s)")
    return 0 if problems == 0 else 1


def cmd_probe_vintage(args) -> int:
    conn = store.connect(args.db)
    print("HEAD on row-level register vintages:")
    for years, status in rijksfinancien.recipients_dataset_available().items():
        print(f"  Financiele_instrumenten_{years}.csv -> {status}")
    row = conn.execute("SELECT max(jaar), max(fetch_id) FROM recipient_line").fetchone()
    print(f"\nstored register covers up to budget year {row[0]}")
    bt = conn.execute("SELECT max(jaar) FROM budget_line").fetchone()[0]
    print(f"stored budget spine covers up to budget year {bt}")
    if row[0] is not None and bt is not None:
        print(f"lag: {int(bt) - int(row[0])} budget year(s)")
    return 0


def cmd_sync(args) -> int:
    args.chapter = getattr(args, "chapter", "VII")
    args.years = getattr(args, "years", "2016-2026")
    rc = cmd_ingest_budget(args)
    if rc:
        return rc
    rc = cmd_ingest_recipients(args)
    if rc:
        return rc
    return cmd_grade(args)


def cmd_provenance(args) -> int:
    conn = store.connect(args.db)
    rows = conn.execute(
        "SELECT fetch_id, source, retrieved_at, n_bytes, licence, url FROM source_fetch ORDER BY retrieved_at"
    ).fetchall()
    if not rows:
        print("no fetches recorded")
        return 1
    for fid, source, when, nbytes, lic, url in rows:
        print(f"{when}  {source}  {nbytes:,}B  {lic}\n    {url}\n    fetch_id={fid}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aer", description=LEDGER_HEADER)
    p.add_argument("--db", default=str(DEFAULT_DB), help="DuckDB store path")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ingest-budget", help="fetch the appropriation spine for one chapter")
    s.add_argument("--chapter", default="VII")
    s.add_argument("--years", default="2016-2026")
    s.set_defaults(func=cmd_ingest_budget)

    s = sub.add_parser("ingest-recipients", help="fetch and load the row-level recipient register")
    s.add_argument("--refresh", action="store_true", help="re-download even if cached")
    s.set_defaults(func=cmd_ingest_recipients)

    s = sub.add_parser("grade", help="grade the party line and write the artifact")
    s.add_argument("--out", default=str(DEFAULT_OUT))
    s.set_defaults(func=cmd_grade)

    s = sub.add_parser("validate", help="integrity checks")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("probe-vintage", help="is the row-level register stale?")
    s.set_defaults(func=cmd_probe_vintage)

    s = sub.add_parser("provenance", help="list recorded fetches")
    s.set_defaults(func=cmd_provenance)

    s = sub.add_parser("sync", help="ingest everything, then grade")
    s.add_argument("--chapter", default="VII")
    s.add_argument("--years", default="2016-2026")
    s.add_argument("--refresh", action="store_true")
    s.add_argument("--out", default=str(DEFAULT_OUT))
    s.set_defaults(func=cmd_sync)

    s = sub.add_parser("ingest-partijfinanciering",
                       help="fetch documents, subsidies, giften from partijfinanciering.nl")
    s.add_argument("--giften-years", default="2022,2023,2024",
                   help="years to fetch gifts for; empty years report no-data-published")
    s.add_argument("--out", default=str(DEFAULT_OUT / "party-financing.csv"),
                   help="artifact CSV to write")
    s.set_defaults(func=cmd_ingest_partijfinanciering)

    s = sub.add_parser("validate-party", help="integrity checks over the party-financing tables")
    s.set_defaults(func=cmd_validate_party)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
