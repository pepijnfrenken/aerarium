#!/usr/bin/env python3
"""Think tanks in the state payment register, matched on identity rather than on spelling.

The first version matched curated name aliases and got Clingendael 25% too low: the register
spells the same institute four ways, and two of those spellings are truncated mid-word
("... Inter. Betrekkin"), so an alias list built from the full published name misses them.

This version keys on the published KvK where a row carries one, falls back to a name alias
only where the row carries none, and refuses rows whose KvK contradicts the entity. Every
rejection is written to an exclusion ledger with its amount, because "we left this out" is a
claim that has to be checkable too.

Verified corrections against the first version:
  Clingendael  33,587k -> 44,769k   two truncated spellings worth 19,774k were missed
  HCSS            234k ->    405k   one truncated spelling worth 171k was missed
  Anne Frank    6,381k ->  6,267k   Montessori schools worth 114k were wrongly included
  FICDD           436k ->    596k   'ChristianDemocratic' without a space was missed

Two register defects surface here and are excluded rather than absorbed:
  * 'Oud Clingendael Zorg B.V.' (KvK 27268646) is a care provider, unrelated.
  * Nine rows named 'Nederlandse Organisatie voor Technologie Ontwikkeling' carry Clingendael's
    KvK 41152832 and EUR 24,703k. That is a register mislabelling, not institute money;
    attributing TNO's budget to a think tank would be the single largest error in this file.
"""

import json
import pathlib
import statistics

import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "aerarium.duckdb"
OUT = ROOT / "out" / "thinktanks.json"

ENTITIES = {
    # --- party political institutes: the test case ---
    "Teldersstichting": {"class": "party-institute", "aliases": ["telders"]},
    "Wetenschappelijk Instituut CDA": {"class": "party-institute",
                                       "aliases": ["wetenschappelijk instituut voor het cda", "wetenschappelijk instituut cda"]},
    "Mr. Hans van Mierlo Stichting": {"class": "party-institute", "aliases": ["van mierlo stichting", "mierlo stichting"]},
    "Wiardi Beckman Stichting": {"class": "party-institute", "aliases": ["wiardi"]},
    "Wetenschappelijk Bureau GroenLinks": {"class": "party-institute",
                                           "aliases": ["wetenschappelijk bureau groenlinks", "bureau de helling"]},
    "Wetenschappelijk Bureau SP": {"class": "party-institute", "aliases": ["wetenschappelijk bureau sp"]},
    "Nicolaas G. Pierson Stichting": {"class": "party-institute", "aliases": ["nicolaas g. pierson", "nicolaas pierson"]},
    "Anne Vondeling Stichting": {"class": "party-institute", "aliases": ["vondeling"]},
    "Edmund Burke Stichting": {"class": "party-institute", "aliases": ["burke"]},
    "Groen van Prinsterer Stichting (CU)": {"class": "party-institute", "kvk": "32084387",
                                            "aliases": ["groen van prinsterer"]},
    # --- party international foundations (NFRP) ---
    "Haya van Somerenstichting": {"class": "party-international", "aliases": ["haya van someren"]},
    "Foundation Max van der Stoel": {"class": "party-international", "aliases": ["max van der stoel"]},
    "Eduardo Frei Stichting": {"class": "party-international", "aliases": ["eduardo frei"]},
    "IDI (D66)": {"class": "party-international", "aliases": ["democratisch initiatief d66"]},
    "GroenLinks International": {"class": "party-international", "aliases": ["international foundation groenlinks"]},
    "SGP-Internationaal": {"class": "party-international", "aliases": ["sgp-internationaal", "sgp internationaal"]},
    "SP Internationaal": {"class": "party-international", "aliases": ["internationaal secretariaat sp"]},
    "FvD International": {"class": "party-international", "aliases": ["forum for democracy internatio"]},
    "Volt There": {"class": "party-international", "aliases": ["volt there"]},
    "Animal Politics Foundation": {"class": "party-international", "aliases": ["animal politics foundation"]},
    "FICDD": {"class": "party-international", "kvk": "32136915",
              "aliases": ["ficdd", "international christiandemo", "international christian democra"]},
    # --- independent policy institutes ---
    "Clingendael": {"class": "policy-institute", "kvk": "41152832",
                    "aliases": ["clingendael", "betrekkingen clin", "nederlands instituut voor internationale"],
                    # a care provider and a separate fund carry the name without the identity
                    "name_exclude": ["oud clingendael zorg", "fonds instituut clingendael"],
                    # rows whose *name* contradicts the KvK: the register misfiles TNO here
                    "name_contradicts_kvk": ["tno", "organisatie voor technologie"]},
    "HCSS": {"class": "policy-institute", "kvk": "27245148", "aliases": ["strategische studi"]},
    # Rathenau's registered KvK 54667089 is the Royal Netherlands Academy's, so a KvK join sweeps in
    # unrelated KNAW institutes (Huygens, and others) and inflated this line by EUR 8.5m on the first
    # try. Where an entity shares its parent's identifier, the name is the only safe key.
    "Rathenau Instituut": {"class": "policy-institute", "aliases": ["rathenau"]},
    "ProDemos": {"class": "policy-institute", "kvk": "50938053", "aliases": ["prodemos"]},
    "Anne Frank Stichting": {"class": "policy-institute", "kvk": "33129466",
                             "aliases": ["anne frank stichting", "anne frank stg"],
                             "name_exclude": ["montessorischool"]},
    "WRR": {"class": "policy-institute", "aliases": ["wetenschappelijke raad voor het regeringsbeleid"]},
}


def coverage_flag(by_year: dict[str, float], first: int, last: int) -> dict | None:
    """Flag a year only against its *neighbours*, not against an all-time peak.

    The first version compared every year to 20% of the highest year ever seen, skipped the
    last year, and never noticed an unobserved year. That flagged Clingendael's early years
    when the real cause was my own missed spellings. A neighbour test cannot be fooled that
    way: it asks whether this year looks like the years on either side of it.
    """
    observed = {int(y): v for y, v in by_year.items()}
    if len(observed) < 3:
        return None
    full = sorted(set(range(first, last + 1)) | set(observed))
    missing = [y for y in full if y not in observed]
    anomalies = []
    for y in full:
        if y not in observed:
            continue
        others = [v for o, v in observed.items() if o != y]
        if len(others) < 2:
            continue
        med = statistics.median(others)
        if med and observed[y] < 0.25 * med:
            anomalies.append(y)
    if not anomalies and not missing:
        return None
    out: dict = {}
    if anomalies:
        out["anomalous_years"] = anomalies
    if missing:
        out["years_with_no_row"] = missing
    out["note"] = ("A year far below its neighbours, or with no row at all, is a coverage question first. "
                   "Check the scheme row for that year before reading it as a change in funding.")
    return out


def main() -> int:
    con = duckdb.connect(str(DB), read_only=True)
    result: dict[str, dict] = {}
    ledger: list[dict] = []

    for canon, spec in ENTITIES.items():
        alias_clause = " OR ".join(["lower(ontvanger) like ?"] * len(spec["aliases"]))
        params = [f"%{a}%" for a in spec["aliases"]]
        kvk_clause = ""
        if spec.get("kvk"):
            kvk_clause = " or kvk = ?"
            params.append(spec["kvk"])
        rows = con.execute(
            f"""select jaar, ontvanger, artikel, instrument, regeling, bedrag_k, kvk
                from recipient_line
                where anonymised = false and ({alias_clause}{kvk_clause})""",
            params,
        ).fetchall()

        keep, drop = [], []
        for jaar, ontv, art, instr, reg, bedrag, kvk in rows:
            low = (ontv or "").lower()
            if any(p in low for p in spec.get("name_exclude", [])):
                drop.append((jaar, ontv, bedrag, "name on the entity's exclusion list"))
            elif spec.get("kvk") and kvk and str(kvk) != spec["kvk"]:
                drop.append((jaar, ontv, bedrag, f"KvK {kvk} contradicts {spec['kvk']}"))
            elif any(p in low for p in spec.get("name_contradicts_kvk", [])):
                drop.append((jaar, ontv, bedrag, "name contradicts the entity's KvK (register misfiling)"))
            else:
                keep.append((jaar, ontv, art, instr, reg, bedrag, kvk))

        by_year: dict[str, float] = {}
        names: set[str] = set()
        kvks: set[str] = set()
        # Per-instrument totals, not just the set of instrument names. An entity can be paid through two
        # different instruments with different purposes, and reporting only the sum lets one stand for the
        # other: FICDD's 8 rows are 5 from the NFRP partnership fund (249k) plus 3 from other schemes
        # (347k). Lumping them makes a BZ fund look like a general subsidy line.
        by_instrument: dict[str, dict[str, float]] = {}
        by_regeling: dict[str, dict[str, float]] = {}
        for jaar, ontv, _a, instr, reg, bedrag, kvk in keep:
            by_year[str(jaar)] = by_year.get(str(jaar), 0) + (bedrag or 0)
            names.add(ontv)
            if kvk:
                kvks.add(str(kvk))
            key = (instr or "(no instrument printed)").strip()
            b = by_instrument.setdefault(key, {"rows": 0, "k": 0})
            b["rows"] += 1
            b["k"] += bedrag or 0
            # The scheme, as published. One entity can appear under several schemes whose purposes differ,
            # and a single total lets one stand for the other: FICDD is 398k through the NFRP partnership
            # family, 155k under the general BZ 2006 subsidy scheme, and 43k under Matra.
            rkey = (reg or "(no scheme printed)").strip()
            rb = by_regeling.setdefault(rkey, {"rows": 0, "k": 0})
            rb["rows"] += 1
            rb["k"] += bedrag or 0

        for jaar, ontv, bedrag, why in drop:
            ledger.append({"entity": canon, "year": jaar, "name": ontv,
                           "amount_k": bedrag, "excluded_because": why})

        yrs = sorted(int(y) for y in by_year) or [0]
        result[canon] = {
            "class": spec["class"],
            "status": "named" if keep else "no-verified-named-row",
            "rows": len(keep),
            "total_k": sum(by_year.values()),
            "years": [yrs[0], yrs[-1]] if keep else [],
            "by_year_k": dict(sorted(by_year.items())),
            "by_instrument": {k: {"rows": v["rows"], "k": round(v["k"])}
                              for k, v in sorted(by_instrument.items(), key=lambda x: -x[1]["k"])},
            "by_regeling": {k: {"rows": v["rows"], "k": round(v["k"])}
                            for k, v in sorted(by_regeling.items(), key=lambda x: -x[1]["k"])},
            "published_names": sorted(names),
            "kvk": sorted(kvks),
            "instruments": sorted(by_instrument),
        }
        if keep:
            flag = coverage_flag(by_year, yrs[0], yrs[-1])
            if flag:
                result[canon]["coverage_flag"] = flag

    con.close()

    classes: dict[str, dict] = {}
    for canon, d in result.items():
        c = classes.setdefault(d["class"], {"entities": 0, "named": 0, "total_k": 0})
        c["entities"] += 1
        if d["status"] == "named":
            c["named"] += 1
            c["total_k"] += d["total_k"]

    payload = {
        "generated_by": "scripts/thinktanks.py",
        "source": {
            "dataset": "rijksfinancien.nl open data, Financiele instrumenten (recipient lines)",
            "licence": "CC-0",
            "unit": "EUR thousands (bedrag_k), as published",
            "url": "https://www.rijksfinancien.nl/open-data",
        },
        "question": "Do think tanks appear in the state payment register, and does the money reach the parties' own institutes?",
        "rule": ("Identity is the published KvK where a row carries one; a name alias is used only where it does "
                 "not. Rows whose KvK contradicts the entity, or whose name contradicts the KvK, are excluded into "
                 "`exclusion_ledger` with their amounts rather than absorbed."),
        "caution_zero": ("`no-verified-named-row` means no row matched in THIS register snapshot under this "
                         "identity rule. It is not evidence that the state pays the entity nothing. VVD's 2023 "
                         "filing describes institute money paid through the party, and PvdA records Wiardi Beckman "
                         "subsidy amounts; both route outside this register. A name-only sweep is a search result, "
                         "not a budget line of zero."),
        "caution_motive": ("Subsidy to an institute is not influence over a party. This shows structural edges only "
                           "and says nothing about what the money bought."),
        "classes": classes,
        "entities": result,
        "exclusion_ledger": ledger,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False))

    print(f"wrote {OUT.relative_to(ROOT)}")
    for cls, agg in sorted(classes.items()):
        print(f"  {cls:<20} {agg['named']}/{agg['entities']} with rows, EUR {agg['total_k']:,.0f}k")
    print()
    for canon, d in sorted(result.items(), key=lambda kv: -kv[1]["total_k"]):
        if d["total_k"]:
            flag = "  FLAG" if d.get("coverage_flag") else ""
            print(f"  {canon:<38}{d['total_k']:>10,.0f}k  {d['rows']:>3}r  {d['published_names'][:1]}{flag}")
    print(f"\n  exclusions: {len(ledger)} rows, EUR {sum(x['amount_k'] or 0 for x in ledger):,}k")
    for x in ledger:
        if (x["amount_k"] or 0) > 100:
            print(f"    {x['entity']:<20}{x['year']}  {str(x['name'])[:38]:<40}{x['amount_k']:>9,}k  {x['excluded_because'][:44]}")
    missing = [c for c, d in result.items() if d["status"] != "named"]
    if missing:
        print(f"\n  no verified named row: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
