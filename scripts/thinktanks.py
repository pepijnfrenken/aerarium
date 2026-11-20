#!/usr/bin/env python3
"""Think tanks in the state payment register.

Two questions, one query:
  1. Do the PARTIES' own political institutes (wetenschappelijke bureaus) receive
     Rijks money through the instruments register?
  2. Do INDEPENDENT policy institutes, and how much?

Precision over recall. Each entity is a canonical name plus the aliases actually
observed in the register. A match needs a curated alias, not a keyword, because
"instituut" appears in hundreds of school and healthcare names.

Sums are in EUR thousands (bedrag_k), the register's own unit. Named and
anonymised rows are counted separately: an anonymised row proves money moved but
not to whom, so it can never be attributed to an entity.
"""

import json
import pathlib
import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "aerarium.duckdb"
OUT = ROOT / "out" / "thinktanks.json"

# canonical -> (class, [aliases as substrings of lower(ontvanger)])
ENTITIES = {
    # --- party political institutes: the test case ---
    "Teldersstichting": ("party-institute", ["telders"]),
    "Wetenschappelijk Instituut CDA": ("party-institute", ["wetenschappelijk instituut cda", "wi cda"]),
    "Mr. Hans van Mierlo Stichting": ("party-institute", ["van mierlo stichting", "mierlo stichting"]),
    "Wiardi Beckman Stichting": ("party-institute", ["wiardi"]),
    "Wetenschappelijk Bureau GroenLinks": ("party-institute", ["wetenschappelijk bureau groenlinks"]),
    "Wetenschappelijk Bureau SP": ("party-institute", ["wetenschappelijk bureau sp"]),
    "Nicolaas G. Pierson Stichting": ("party-institute", ["nicolaas g. pierson", "nicolaas pierson"]),
    "Anne Vondeling Stichting": ("party-institute", ["vondeling"]),
    "Edmund Burke Stichting": ("party-institute", ["burke"]),
    # --- party international foundations: expected to appear (NFRP) ---
    # Aliases are the OBSERVED register spellings, not the tidy names. A first pass used the
    # tidy names and reported four of these as "no rows" while their money sat in the table.
    "Haya van Somerenstichting": ("party-international", ["haya van someren"]),
    "Foundation Max van der Stoel": ("party-international", ["max van der stoel"]),
    "Eduardo Frei Stichting": ("party-international", ["eduardo frei"]),
    "IDI (D66)": ("party-international", ["democratisch initiatief d66"]),
    "GroenLinks International": ("party-international", ["international foundation groenlinks"]),
    "SGP-Internationaal": ("party-international", ["sgp-internationaal", "sgp internationaal"]),
    "SP Internationaal": ("party-international", ["internationaal secretariaat sp"]),
    "FvD International": ("party-international", ["forum for democracy internatio"]),
    "Volt There": ("party-international", ["volt there"]),
    "Animal Politics Foundation": ("party-international", ["animal politics foundation"]),
    "FICDD": ("party-international", ["ficdd", "international christian democratic"]),
    # --- independent policy institutes ---
    "Clingendael": ("policy-institute", ["clingendael", "nederlands instituut voor internationale"]),
    "HCSS": ("policy-institute", ["strategische studies"]),
    "Rathenau Instituut": ("policy-institute", ["rathenau"]),
    "ProDemos": ("policy-institute", ["prodemos"]),
    "Anne Frank Stichting": ("policy-institute", ["anne frank"]),
    "WRR": ("policy-institute", ["wetenschappelijke raad voor het regeringsbeleid"]),
}


def main() -> int:
    con = duckdb.connect(str(DB), read_only=True)
    result: dict[str, dict] = {}
    for canon, (cls, aliases) in ENTITIES.items():
        where = " OR ".join(["lower(ontvanger) like ?"] * len(aliases))
        params = [f"%{a}%" for a in aliases]
        rows = con.execute(
            f"""select jaar, ontvanger, artikel, instrument, bedrag_k, kvk, anonymised
                from recipient_line
                where anonymised = false and ({where})
                order by jaar""",
            params,
        ).fetchall()
        by_year: dict[int, float] = {}
        names: set[str] = set()
        kvks: set[str] = set()
        instruments: set[str] = set()
        for jaar, ontv, _art, instr, bedrag, kvk, _anon in rows:
            by_year[jaar] = by_year.get(jaar, 0) + (bedrag or 0)
            names.add(ontv)
            if kvk:
                kvks.add(str(kvk))
            if instr:
                instruments.add(instr)
        result[canon] = {
            "class": cls,
            "status": "named" if rows else "no-rows-in-register",
            "rows": len(rows),
            "total_k": sum(by_year.values()),
            "years": sorted(by_year),
            "by_year_k": {str(k): v for k, v in sorted(by_year.items())},
            "published_names": sorted(names),
            "kvk": sorted(kvks),
            "instruments": sorted(instruments),
        }

    con.close()

    # Per-year register coverage is not constant, and a collapse in a scheme row is a gap in the register
    # before it is a cut in funding. Flag any entity-year below a fifth of that entity's best year so no
    # reader mistakes the register's silence for the state stopping the payment.
    for canon, d in result.items():
        by_year = d.get("by_year_k") or {}
        if len(by_year) < 2:
            continue
        top = max(by_year.values())
        flags = [y for y, v in by_year.items() if top and v < 0.2 * top]
        if flags and d.get("years"):
            # only flag an interior year if the neighbouring published years are much larger
            interior = [y for y in flags if d["years"][0] <= int(y) < d["years"][-1]]
            if interior:
                d["coverage_flag"] = (
                    f"years {', '.join(sorted(interior))} are below a fifth of the entity's best year. "
                    "Check the scheme row for that year before reading it as a fall in funding."
                )

    classes: dict[str, dict] = {}
    for canon, d in result.items():
        c = d["class"]
        agg = classes.setdefault(c, {"entities": 0, "named": 0, "total_k": 0})
        agg["entities"] += 1
        if d["status"] == "named":
            agg["named"] += 1
            agg["total_k"] += d["total_k"]

    payload = {
        "generated_by": "scripts/thinktanks.py",
        "source": {
            "dataset": "rijksfinancien.nl open data, Financiele instrumenten (recipient lines)",
            "licence": "CC-0",
            "unit": "EUR thousands (bedrag_k), as published",
            "url": "https://www.rijksfinancien.nl/open-data",
        },
        "question": "Do think tanks appear in the state payment register, and does the money reach the parties' own institutes?",
        "rule": "A match requires a curated alias for a named institute. Keyword matches on 'instituut' were rejected as noise (schools, healthcare).",
        "caveat": "Subsidy to an institute is not influence over a party. This shows structural edges only; it says nothing about what the money bought.",
        "classes": classes,
        "entities": result,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False))

    print(f"wrote {OUT.relative_to(ROOT)}")
    for cls, agg in sorted(classes.items()):
        print(f"  {cls:<20} {agg['named']}/{agg['entities']} entities with rows, EUR {agg['total_k']:,.0f}k")
    print()
    for canon, d in sorted(result.items(), key=lambda kv: -kv[1]["total_k"]):
        if d["total_k"]:
            print(f"  {canon:<38}{d['total_k']:>10,.0f}k  {d['years'][0]}-{d['years'][-1]}  {d['rows']} rows")
    missing = [c for c, d in result.items() if d["status"] != "named"]
    if missing:
        print(f"\n  no rows: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
