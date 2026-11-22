#!/usr/bin/env python3
"""Proof of flow: how far each euro can be followed, measured at the level the registers allow.

The premise that failed (docs/PROBE-006): recipients do not sum to chapter totals. They are not meant
to. Chapter XVI appropriates EUR 765.793k for article "Langdurige zorg en ondersteuning" while the
recipient register publishes EUR 21.519.845k under the same heading, because the Wlz flows through the
Zorginstituut financed largely by premiums. The register records all payments in a policy domain; the
chapter records the appropriation's contribution to it. Dividing one by the other produces a number
that is neither a disclosure grade nor a flow.

So the flow is measured in three separate ways, and never collapsed into one:

  A. REACHABILITY (budget side, in euros). Of realised expenditure, how much sits under an instrument
     type for which the recipient register ever publishes a named recipient? That is the ceiling on
     what could ever be traced. Everything else stops at r3 by design, and saying so is the finding.

  B. DISCLOSURE GRADE (register side, in euros). Of the money the register publishes, how much is
     named and how much is anonymised, per year. Valid within the register, and it shows three
     regimes rather than a trend.

  C. THE CLAIM JOIN. Where budget and register name the same (year, chapter, article, instrument), the
     amounts are compared and classified: close, multiplier (the premium-funded case), budget-only,
     register-only. This is a claim about matching labels, not a sum, so the match rates are reported.

Every figure carries its year. Nothing is expressed as a percentage of a total it does not belong to.
"""

from __future__ import annotations

import json
import pathlib
import unicodedata

import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "aerarium.duckdb"
OUT = ROOT / "out" / "flow.json"

# The register spells one instrument differently from the budget tables.
INSTRUMENT_ALIASES = {
    "bijdrage aan zbos en rwts": "bijdrage aan zbo's/rwt's",
}

# Chapter codes that exist on one side only. Recorded, not silently dropped.
CHAPTER_ALIASES = {
    "j": "III",   # Algemene Zaken appears as J in the register in some years
    "k": "XVIII", # Wonen en Rijksdienst
}


def norm(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = " ".join(s.lower().split())
    return INSTRUMENT_ALIASES.get(s, s)


def main() -> int:
    con = duckdb.connect(str(DB), read_only=True)
    B = "(select distinct * from budget_line)"

    years = [r[0] for r in con.execute(f"select distinct jaar from {B} order by 1").fetchall()]

    # ---------------------------------------------------------------- A. reachability
    # Two financing bases sit in the same series and must not be compared across the break:
    # appropriation-financed expenditure, and expenditure financed by premiums
    # (`Premiegefinancieerde zorgverzekeringswet`, `... Wet langdurige zorg`, and in 2016
    # `Premiegefinancierde Inkomensoverdrachten`). Those labels appear from 2016 to 2019 and then stop,
    # without the money disappearing: the Wlz and Zvw flows keep being paid, they stop being booked as
    # chapter rows here. So publishing one line across 2016-2025 would show a coverage break as a rise
    # in reachability. Both bases are reported, and no harmonised national total is claimed.
    reachable = {norm(r[0]) for r in con.execute(
        "select distinct instrument from recipient_line where instrument is not null"
    ).fetchall()}

    exp_by_year: dict[int, dict[str, float]] = {}
    for jaar, instr, k in con.execute(
        f"""select jaar, coalesce(instrument_naam,''), sum(bedrag_k) from {B}
            where fase='JV' and vuo='U' and bedrag_k is not null group by 1,2"""
    ).fetchall():
        low = instr.lower()
        e = exp_by_year.setdefault(jaar, {"reachable": 0.0, "unreachable": 0.0, "premium": 0.0})
        if "premie" in low:
            e["premium"] += k or 0
            continue
        if low in ("leningen", "mutaties in rekening-courant en deposito's",
                   "vermogensverschaffing/-onttrekking",
                   "storting/onttrekking begrotingsreserve"):
            continue
        if "ontvangsten" in low:
            continue
        if "andere" in low and "begroting" in low:
            continue
        key = norm(instr)
        e["reachable" if key in reachable else "unreachable"] += k or 0

    reach = []
    for jaar in sorted(exp_by_year):
        e = exp_by_year[jaar]
        tot = e["reachable"] + e["unreachable"]
        reach.append({
            "year": jaar,
            "appropriation_expenditure_k": round(tot),
            "reachable_k": round(e["reachable"]),
            "unreachable_k": round(e["unreachable"]),
            "reachable_pct": round(100 * e["reachable"] / tot, 1) if tot else None,
            "premium_financed_k": round(e["premium"]),
        })

    # ---------------------------------------------------------------- B. disclosure grade
    grade = []
    for jaar, rows, anon_rows, anon_k, named_k in con.execute(
        """select jaar, count(*), sum(case when anonymised then 1 else 0 end),
                  sum(case when anonymised then bedrag_k else 0 end),
                  sum(case when not anonymised then bedrag_k else 0 end)
           from recipient_line group by 1 order by 1"""
    ).fetchall():
        anon_k, named_k = anon_k or 0, named_k or 0
        tot = anon_k + named_k
        grade.append({
            "year": jaar,
            "rows": rows,
            "anonymised_rows": anon_rows,
            "named_k": named_k,
            "anonymised_k": anon_k,
            "named_pct": round(100 * named_k / tot, 1) if tot else None,
        })

    # ---------------------------------------------------------------- C. the claim join
    # Match on (year, chapter, article name, instrument name), all normalised. Amounts are compared
    # but never summed together: they measure different quantities by construction.
    b_rows = con.execute(
        f"""select jaar, hoofdstuk_nummer, artikel_naam, instrument_naam, sum(bedrag_k)
            from {B} where fase='JV' and vuo='U' and bedrag_k is not null group by 1,2,3,4"""
    ).fetchall()
    r_rows = con.execute(
        """select jaar, hoofdstuk, artikel, instrument, sum(bedrag_k)
           from recipient_line group by 1,2,3,4"""
    ).fetchall()

    bmap: dict[tuple, float] = {}
    for jaar, ch, art, instr, k in b_rows:
        ch = CHAPTER_ALIASES.get(ch.lower(), ch) if ch else ch
        key = (jaar, ch, norm(art), norm(instr))
        # Aggregate, never overwrite: two raw spellings that normalise to the same key are one line,
        # and letting the last row win silently dropped the other's money and changed the buckets.
        bmap[key] = bmap.get(key, 0.0) + (k or 0)
    rmap: dict[tuple, float] = {}
    for jaar, ch, art, instr, k in r_rows:
        ch = CHAPTER_ALIASES.get(ch.lower(), ch) if ch else ch
        key = (jaar, ch, norm(art), norm(instr))
        rmap[key] = rmap.get(key, 0.0) + (k or 0)

    common = set(bmap) & set(rmap)
    close = mult_big = mult_small = nonpositive = 0
    for key in common:
        b, r = bmap[key], rmap[key]
        if b <= 0 or r <= 0:
            nonpositive += 1
            continue
        ratio = r / b
        if 0.98 <= ratio <= 1.02:
            close += 1
        elif ratio > 1.02:
            mult_big += 1
        else:
            mult_small += 1

    total_b = len(bmap)
    total_r = len(rmap)
    join_stats = {
        "budget_groups": total_b,
        "register_groups": total_r,
        "matched_groups": len(common),
        "match_rate_of_register_pct": round(100 * len(common) / total_r, 1) if total_r else None,
        "matched_agreeing_within_2pct": close,
        "matched_register_exceeds_budget": mult_big,
        "matched_budget_exceeds_register": mult_small,
        "matched_with_a_nonpositive_side": nonpositive,
        "budget_only": total_b - len(common),
        "register_only": total_r - len(common),
        "note": ("A matched group is a claim that two registers describe the same instrument line. "
                 "Rows are aggregated after normalisation, so two spellings of one line are one group. "
                 "Where the register exceeds the budget it is usually a scheme financed outside the "
                 "appropriation (premium-funded care, fund flows); where the budget exceeds the register "
                 "it is usually an instrument type for which no recipient is published. Groups with a "
                 "positive and a nonpositive side are counted separately and left unclassified, because "
                 "a ratio against zero or a credit is not a comparison. Neither is summed across."),
    }

    # the three worked examples that carry the argument, compared at ARTICLE level because the two
    # registers book the same article under different instrument splits (XVI has no 'Bekostiging'
    # line on the budget side at all: the appropriation sits under other instruments entirely)
    def art_totals(src, jaar, ch, art, key_art, key_ch):
        return sum(v for k, v in src.items()
                   if k[0] == jaar and k[1] == ch and k[key_art] == norm(art))

    examples = []
    for jaar, ch, art, instr in [
        (2024, "XVI", "Langdurige zorg en ondersteuning", "Bekostiging"),
        (2024, "XVI", "Curatieve zorg", "Bekostiging"),
        (2024, "IX", None, "Leningen"),
    ]:
        if art is None:
            b = sum(v for k, v in bmap.items() if k[0] == jaar and k[1] == ch and k[3] == norm(instr))
            r = sum(v for k, v in rmap.items() if k[0] == jaar and k[1] == ch and k[3] == norm(instr))
        else:
            b = art_totals(bmap, jaar, ch, art, 2, 1)
            r = art_totals(rmap, jaar, ch, art, 2, 1)
        examples.append({
            "year": jaar, "chapter": ch, "article": art, "instrument": instr,
            "basis": "article" if art else "instrument",
            "budget_k": b, "register_k": r,
            "ratio": round(r / b, 1) if b else None,
        })

    payload = {
        "generated_by": "scripts/flow.py",
        "question": "How far down the chain of custody does each euro survive?",
        "measures": {
            "reachability": ("Budget side, in euros: appropriation-financed expenditure sitting under an "
                             "instrument type for which a recipient is ever published. A ceiling on "
                             "traceability, not a claim that those euros were traced."),
            "disclosure_grade": ("Register side, in euros: named versus anonymised among the money the "
                                 "register publishes. Valid within the register only."),
            "claim_join": ("Matching labels across the two registers. Counts, not sums: the two registers "
                           "measure different quantities on the same line."),
            "financing_basis": ("Premium-financed expenditure is reported apart from appropriation-financed "
                                "expenditure. The premium labels exist from 2016 to 2019 only, so the two "
                                "bases cannot be compared across that break and no harmonised national "
                                "total is claimed for the period."),
        },
        "reachability": reach,
        "disclosure_grade": grade,
        "claim_join": join_stats,
        "examples": examples,
        "chapter_code_mismatch": {
            "note": ("The register uses J and K where the budget uses III and XVIII for some years. "
                     "Aliased in this script and counted in the join; recorded here rather than "
                     "silently repaired."),
            "aliases": CHAPTER_ALIASES,
        },
        "years": years,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"wrote {OUT.relative_to(ROOT)}")
    print("\nA. reachability, appropriation-financed (premium-financed shown separately)")
    for r in reach:
        print(f"   {r['year']}  approp {r['appropriation_expenditure_k']:>14,}k  reachable {r['reachable_pct']:>5.1f}%"
              f"   premium {r['premium_financed_k']:>13,}k")
    print("\nB. disclosure grade within the register")
    for g in grade:
        print(f"   {g['year']}  named {g['named_k']:>14,}k  anon {g['anonymised_k']:>14,}k  named {g['named_pct']:>5.1f}%")
    print("\nC. the claim join")
    for k, v in join_stats.items():
        if k != "note":
            print(f"   {k:<38}{v}")
    print("\nexamples")
    for e in examples:
        print(f"   {e['year']} {e['chapter']:<4}{(e['article'] or '')[:34]:<36}{e['instrument'][:16]:<18}"
              f"budget {format(e['budget_k'] or 0, ','):>14}  register {format(e['register_k'] or 0, ','):>14}"
              f"  x{e['ratio'] if e['ratio'] is not None else 'n/a'}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
