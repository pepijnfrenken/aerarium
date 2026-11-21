#!/usr/bin/env python3
"""The government run: what each ministry spends, and how much of it goes on itself.

Three questions, answered per chapter rather than as one national total, because a single figure hides
exactly the variation that matters:

  1. How big is each ministry on the realised account (JV), and in what?
  2. How far does the realised figure sit from the draft ceiling (OWB)?
  3. How much of it is personnel, and can that even be answered from this source?

Two things this file measures before it reports, because both were asserted from schema presence and
both turned out wrong:

  * `beleid_of_niet_beleid` exists as a column and is BLANK in every row of every year. It does not
    split policy from apparatus. The count is printed so the claim is checkable.
  * `Personele uitgaven` exists as an instrument but is not applied uniformly: some chapters book
    personnel under it, others book the same money as a contribution to an agency or as an opdracht.
    A national percentage over this instrument measures which ministries use the label, not the
    state's wage bill. Per-chapter personnel is reported; the national share is reported with that
    warning attached.

Phases: the API serves OWB (draft) and JV (realised) and NOT O1/O2, the supplementary budgets. So the
"ceiling" here is the draft ceiling, and the distance between draft and account includes every
Voorjaarsnota and Najaarsnota this source cannot show. Say so next to the number.

Rows are deduplicated at read time (SELECT DISTINCT) rather than by rebuilding the table: several steps
and agents read this store, and a rewrite is not mine to make on my own initiative.
"""

from __future__ import annotations

import json
import pathlib

import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "aerarium.duckdb"
OUT = ROOT / "out" / "govrun.json"
LATEST_FULL = 2024  # last year with both a draft and a realised account


def main() -> int:
    con = duckdb.connect(str(DB), read_only=True)
    D = "(select distinct * from budget_line)"

    # --- column integrity, measured rather than assumed -------------------------
    blank_by_year = con.execute(
        f"""select jaar,
                   count(*) as rows,
                   sum(case when beleid_of_niet_beleid is null
                              or trim(beleid_of_niet_beleid) = '' then 1 else 0 end) as blank
            from {D} group by 1 order by 1"""
    ).fetchall()

    # --- chapter shape on the realised account ---------------------------------
    chapters = con.execute(
        f"""select hoofdstuk_nummer,
                   min(hoofdstuk_naam),
                   count(distinct jaar),
                   min(jaar), max(jaar)
            from {D} group by 1 order by 1"""
    ).fetchall()

    # --- 2024: realised, draft, and the instrument split -----------------------
    rows_2024 = con.execute(
        f"""
        with jv as (select hoofdstuk_nummer ch, sum(bedrag_k) tot
                    from {D} where fase='JV' and jaar={LATEST_FULL} and bedrag_k is not null group by 1),
             owb as (select hoofdstuk_nummer ch, sum(bedrag_k) tot
                    from {D} where fase='OWB' and jaar={LATEST_FULL} and bedrag_k is not null group by 1),
             ins as (select hoofdstuk_nummer ch,
                       sum(case when instrument_naam = 'Personele uitgaven' then bedrag_k else 0 end) pers,
                       sum(case when instrument_naam = 'Materiële uitgaven' then bedrag_k else 0 end) mat,
                       sum(case when instrument_naam like 'Subsidies%' then bedrag_k else 0 end) sub,
                       sum(case when instrument_naam like 'Opdrachten%' then bedrag_k else 0 end) opd
                    from {D} where fase='JV' and jaar={LATEST_FULL} and bedrag_k is not null group by 1),
             nm as (select hoofdstuk_nummer ch, min(hoofdstuk_naam) naam from {D} group by 1)
        select nm.ch, nm.naam, jv.tot, owb.tot, ins.pers, ins.mat, ins.sub, ins.opd
        from nm join jv using(ch) left join owb using(ch) left join ins using(ch)
        order by jv.tot desc
        """
    ).fetchall()

    per_chapter = []
    for ch, naam, jv, owb, pers, mat, sub, opd in rows_2024:
        jv = jv or 0
        per_chapter.append({
            "chapter": ch,
            "name": naam,
            "realised_k": jv,
            "draft_ceiling_k": owb,
            "delta_k": (jv - owb) if owb is not None else None,
            "delta_pct": round(100 * (jv - owb) / owb, 1) if owb else None,
            "personnel_k": pers or 0,
            "personnel_share_pct": round(100 * (pers or 0) / jv, 1) if jv else None,
            "material_k": mat or 0,
            "material_share_pct": round(100 * (mat or 0) / jv, 1) if jv else None,
            "subsidies_k": sub or 0,
            "opdrachten_k": opd or 0,
            "uses_personnel_instrument": bool(pers),
        })

    # --- personnel series per chapter, with the years that actually carry a row -
    series: dict[str, dict[int, float]] = {}
    for ch, jaar, k in con.execute(
        f"""select hoofdstuk_nummer, jaar, sum(bedrag_k)
            from {D} where fase='JV' and instrument_naam='Personele uitgaven' and bedrag_k is not null
            group by 1,2 order by 1,2"""
    ).fetchall():
        series.setdefault(ch, {})[int(jaar)] = k

    # --- which instruments carry money, per chapter (shows the label is optional)
    instrument_use = {}
    for ch, instr, k in con.execute(
        f"""select hoofdstuk_nummer, coalesce(instrument_naam,'(blank)'), sum(bedrag_k)
            from {D} where fase='JV' and jaar={LATEST_FULL} and bedrag_k is not null
            group by 1,2 order by 1, 3 desc"""
    ).fetchall():
        instrument_use.setdefault(ch, []).append({"instrument": instr, "amount_k": k})

    # --- what the instrument dimension actually contains ------------------------
    # A chapter total summed straight off the account is not spending. Three categories sit inside it
    # that are not money leaving the state for goods, people or transfers:
    #   receipts            money coming IN, summed as though it were expenditure
    #   inter-chapter       one chapter paying another; double counts if chapters are added
    #   financial           loans and treasury movements, which create an asset or repay one
    # Each is named so a reader can disagree with the classification and recompute.
    def instrument_class(instr: str) -> str:
        i = (instr or "").lower()
        if "ontvangsten" in i:
            return "receipts"
        if "andere" in i and "begroting" in i:
            return "inter_chapter_transfer"
        if i in ("leningen", "mutaties in rekening-courant en deposito's",
                 "vermogensverschaffing/-onttrekking", "storting/onttrekking begrotingsreserve"):
            return "financial_transaction"
        return "expenditure"

    classified: dict[str, dict[str, float]] = {}
    for instr, k in con.execute(
        f"""select coalesce(instrument_naam,'(blank)') i, sum(bedrag_k)
            from {D} where fase='JV' and jaar={LATEST_FULL} and bedrag_k is not null group by 1"""
    ).fetchall():
        cls = instrument_class(instr)
        classified.setdefault(cls, {})[instr] = k

    class_totals = {c: sum(v.values()) for c, v in classified.items()}

    # per chapter, expenditure only, so a ministry's size is its programme and people
    per_chapter_net: dict[str, float] = {}
    for ch, instr, k in con.execute(
        f"""select hoofdstuk_nummer, coalesce(instrument_naam,'(blank)'), sum(bedrag_k)
            from {D} where fase='JV' and jaar={LATEST_FULL} and bedrag_k is not null group by 1,2"""
    ).fetchall():
        if instrument_class(instr) == "expenditure":
            per_chapter_net[ch] = per_chapter_net.get(ch, 0) + (k or 0)

    total_jv = sum(r["realised_k"] for r in per_chapter)
    total_pers = sum(r["personnel_k"] for r in per_chapter)
    total_owb = sum(r["draft_ceiling_k"] or 0 for r in per_chapter)
    zero_personnel = [r["chapter"] for r in per_chapter if not r["uses_personnel_instrument"]]
    net_total = sum(per_chapter_net.values())

    for r in per_chapter:
        r["expenditure_k"] = per_chapter_net.get(r["chapter"], 0)
        r["non_expenditure_k"] = r["realised_k"] - r["expenditure_k"]

    payload = {
        "generated_by": "scripts/govrun.py",
        "source": {
            "dataset": "rijksfinancien.nl open data, budgettaire tabellen (all chapters)",
            "licence": "CC-0",
            "unit": "EUR thousands (bedrag_k), as published",
            "phases": "OWB = draft budget (ontwerpbegroting), JV = realised account (jaarverslag)",
        },
        "limits": {
            "supplementary_budgets": ("O1/O2, the suppletoire wetten, are not served by this API: every query "
                                      "returns the same unfiltered set. The ceiling here is the DRAFT ceiling, and "
                                      "the distance to the account includes every Voorjaarsnota and Najaarsnota "
                                      "this source cannot show."),
            "beleid_of_niet_beleid": ("The column exists and is blank in every row of every year. It does NOT "
                                      "split policy from apparatus spending, and no figure here relies on it."),
            "personnel_instrument": ("'Personele uitgaven' is an instrument line, not an apparatus total. "
                                     "Chapters that book personnel as a contribution to an agency or as an "
                                     "opdracht show zero here. The national share measures who uses the label, "
                                     "not the state's wage bill. Per-chapter figures are given; the national "
                                     "share carries this warning."),
            "duplicates": ("Read-time SELECT DISTINCT. The store holds exact duplicate rows from repeated loads "
                           "(94 at last count); deduplicating in the query rather than rebuilding the table."),
        },
        "column_integrity": {
            "beleid_of_niet_beleid_blank_by_year": [
                {"year": y, "rows": n, "blank": b} for y, n, b in blank_by_year
            ],
            "verdict": "blank in every row" if all(b == n for _, n, b in blank_by_year) else "partly populated",
        },
        "chapters": [
            {"chapter": ch, "name": nm, "years": ny, "first": f, "last": l}
            for ch, nm, ny, f, l in chapters
        ],
        "year": LATEST_FULL,
        "national": {
            "gross_chapter_sum_k": total_jv,
            "expenditure_k": net_total,
            "not_expenditure_k": total_jv - net_total,
            "draft_ceiling_k": total_owb,
            "personnel_k": total_pers,
            "personnel_share_of_expenditure_pct": round(100 * total_pers / net_total, 1) if net_total else None,
            "chapters_with_no_personnel_instrument": zero_personnel,
            "note": ("gross_chapter_sum_k is what adding the chapters gives, and it is NOT spending: it contains "
                     "receipts, inter-chapter transfers and financial transactions. expenditure_k removes the "
                     "three categories named in instrument_classes."),
        },
        "instrument_classes": {
            cls: {
                "total_k": round(k, 0),
                "share_of_gross_pct": round(100 * k / total_jv, 1) if total_jv else None,
                "instruments": {i: v for i, v in sorted(vals.items(), key=lambda kv: -kv[1])},
            }
            for cls, (k, vals) in {
                c: (class_totals.get(c, 0), classified.get(c, {})) for c in
                ("expenditure", "receipts", "inter_chapter_transfer", "financial_transaction")
            }.items()
        },
        "per_chapter": per_chapter,
        "personnel_series_by_chapter": {
            ch: {str(y): v for y, v in sorted(ys.items())} for ch, ys in sorted(series.items())
        },
        "instrument_use": instrument_use,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  column integrity: beleid_of_niet_beleid {payload['column_integrity']['verdict']}")
    nat = payload["national"]
    print(f"\n  gross chapter sum      EUR {nat['gross_chapter_sum_k']:,}k")
    print(f"  of which not spending  EUR {nat['not_expenditure_k']:,}k")
    for cls in ("receipts", "inter_chapter_transfer", "financial_transaction"):
        c = payload["instrument_classes"][cls]
        print(f"    {cls:<24}EUR {c['total_k']:>15,.0f}k  {c['share_of_gross_pct']:>5.1f}%")
    print(f"  expenditure            EUR {nat['expenditure_k']:,}k")
    print(f"  personnel              EUR {nat['personnel_k']:,}k = {nat['personnel_share_of_expenditure_pct']}% of expenditure")
    print(f"  no personnel row: {', '.join(nat['chapters_with_no_personnel_instrument']) or 'none'}")
    print(f"\n  {'ch':<4}{'ministry':<38}{'expenditure k':>15}{'non-exp k':>12}{'personnel':>12}{'%exp':>7}")
    for r in sorted(per_chapter, key=lambda x: -x["expenditure_k"]):
        pct = (100 * r["personnel_k"] / r["expenditure_k"]) if r["expenditure_k"] else 0
        print(f"  {r['chapter']:<4}{str(r['name'])[:36]:<38}{r['expenditure_k']:>15,}{r['non_expenditure_k']:>12,}"
              f"{r['personnel_k']:>12,}{pct:>7.1f}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
