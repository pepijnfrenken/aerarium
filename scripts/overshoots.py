#!/usr/bin/env python3
"""Emit every chapter x instrument-type overshoot on the realised basis, classified, with its numbers.

WHY THE BASIS IS JV. `budget_line` stores two phases per year: `OWB` (the draft budget) and `JV` (the jaarverslag,
the realised account). The first version of this script summed both, which produced "appropriations" that were
draft plus realised: chapter XVI 2024 `Bekostiging` read as EUR 435.738k because 235.885k of draft had been added
to 199.853k of realised. The recipient register records payments actually made, so the only defensible comparator
is the realised figure. The all-phase sum is still emitted, under `diagnostic_all_phases`, so the superseded
number stays traceable; it must never be used for a comparison.

Nonpositive budgets are carried, not hidden. A negative appropriation (a credit line) or a zero one has no
percentage-over-baseline meaning, so those rows keep their signed delta and are flagged rather than classified by
ratio. Transfer amounts are nullable: a missing row is `null`, not zero, because a chapter with no transfer row has
not been shown to have transferred nothing.

Classes, each an interpretation laid over a measured delta:
  outside-appropriation  instrument financed by premiums or social funds, so the appropriation line is symbolic
  transfer-structure     the chapter-year carries a positive transfer appropriation; no edge is traced from it here
  unexplained            neither of the above
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "data" / "aerarium.duckdb"
OUT = REPO / "out" / "overshoots.json"

OUTSIDE = ("Bekostiging", "Bijdrage aan sociale fondsen")
TRANSFER = "Bijdrage aan (andere) begrotingshoofdstukken"
BASIS = "JV"


def groups(con, phase: str | None) -> list[tuple]:
    phase_sql = "" if phase is None else "and fase = ?"
    args = [] if phase is None else [phase]
    return con.execute(f"""
        with b as (select jaar, hoofdstuk_nummer as h, instrument_naam as i, sum(bedrag_k) as bud
                   from budget_line where vuo='U' {phase_sql} group by 1,2,3),
             r as (select jaar, hoofdstuk as h, instrument as i, sum(bedrag_k) as rec
                   from recipient_line group by 1,2,3)
        select b.jaar, b.h, b.i, b.bud, r.rec
        from b join r using (jaar, h, i)
        where r.rec > b.bud * 1.02
        order by (r.rec - b.bud) desc
    """, args).fetchall()


def bucket_split(con, phase: str) -> tuple:
    """Joined groups three ways: at or below, above but inside the tolerance, above it."""
    return con.execute("""
        with b as (select jaar, hoofdstuk_nummer as h, instrument_naam as i, sum(bedrag_k) as bud
                   from budget_line where vuo='U' and fase=? group by 1,2,3),
             r as (select jaar, hoofdstuk as h, instrument as i, sum(bedrag_k) as rec
                   from recipient_line group by 1,2,3)
        select count(*),
               sum(case when r.rec <= b.bud then 1 else 0 end),
               sum(case when r.rec > b.bud and r.rec <= b.bud*1.02 then 1 else 0 end),
               sum(case when r.rec > b.bud*1.02 then 1 else 0 end)
        from b join r using (jaar,h,i)
    """, [phase]).fetchone()


def coverage(con, phase: str | None) -> dict:
    args = [] if phase is None else [phase]
    phase_sql = "" if phase is None else "and fase = ?"
    r = con.execute(f"""
        with ty as (select distinct instrument from recipient_line where instrument is not null),
             b as (select instrument_naam as i, sum(bedrag_k) as s
                   from budget_line where vuo='U' {phase_sql} group by 1)
        select coalesce(sum(case when b.i is not null and b.i<>'' and exists
                    (select 1 from ty where ty.instrument=b.i) then b.s end),0),
               coalesce(sum(case when b.i is null or b.i='' or b.i='0' then b.s end),0),
               coalesce(sum(case when b.i is not null and b.i<>'' and b.i<>'0' and not exists
                    (select 1 from ty where ty.instrument=b.i) then b.s end),0),
               sum(b.s)
        from b
    """, args).fetchone()
    total = r[3]
    return {
        "expenditure_total_k": round(total),
        "joinable_k": round(r[0]),
        "joinable_share": round(r[0] / total, 4),
        "blank_or_zero_label_k": round(r[1]),
        "blank_or_zero_share": round(r[1] / total, 4),
        "other_policy_label_k": round(r[2]),
        "other_policy_share": round(r[2] / total, 4),
    }


def main() -> int:
    con = duckdb.connect(DB, read_only=True)
    try:
        rows = []
        for jaar, ch, inst, bud, rec in groups(con, BASIS):
            tb, trn, nr, nrr = con.execute("""
                select
                  (select sum(bedrag_k) from budget_line
                    where vuo='U' and fase=? and jaar=? and hoofdstuk_nummer=? and instrument_naam=?),
                  (select sum(bedrag_k) from recipient_line
                    where jaar=? and hoofdstuk=? and instrument=?),
                  (select count(*) from budget_line
                    where vuo='U' and fase=? and jaar=? and hoofdstuk_nummer=? and instrument_naam=?),
                  (select count(*) from recipient_line
                    where jaar=? and hoofdstuk=? and instrument=?)""",
                [BASIS, jaar, ch, TRANSFER, jaar, ch, TRANSFER,
                 BASIS, jaar, ch, TRANSFER, jaar, ch, TRANSFER]).fetchone()
            if inst in OUTSIDE:
                cls = "outside-appropriation"
            elif tb is not None and tb > 0:
                cls = "transfer-structure"
            else:
                cls = "unexplained"
            rows.append({
                "jaar": jaar, "chapter": ch, "instrument": inst,
                "budget_k": round(bud), "register_k": round(rec), "overshoot_k": round(rec - bud),
                "budget_nonpositive": bud <= 0,
                "transfer_budget_k": None if tb is None else round(tb),
                "transfer_register_k": None if trn is None else round(trn),
                "transfer_budget_rows": nr,
                "transfer_register_rows": nrr,
                "class": cls,
            })

        cov = coverage(con, BASIS)
        split = bucket_split(con, BASIS)
        cov_all = coverage(con, None)
        all_rows = groups(con, None)
        rbv = con.execute(
            "select count(*), sum(case when coalesce(rbv_model,'')='' then 1 else 0 end) "
            "from (select distinct * from budget_line) where vuo='U'").fetchone()
    finally:
        con.close()

    by_class: dict[str, dict] = {}
    for r in rows:
        c = by_class.setdefault(r["class"], {"groups": 0, "overshoot_k": 0})
        c["groups"] += 1
        c["overshoot_k"] += r["overshoot_k"]

    payload = {
        "generated_by": "scripts/overshoots.py",
        "basis": BASIS,
        "basis_note": ("The comparator is the realised account (fase='JV'), because the recipient register records "
                       "payments actually made. fase='OWB' is the draft budget and is never added to it. 2026 has "
                       "no realised account yet, so this join covers 2016-2025."),
        "definition": ("A group is one (year, chapter, instrument type) where the recipient register records more "
                       "money than the realised appropriation carries, by more than 2%."),
        "why_2_percent": ("Rounding and re-publication move a line by small amounts; 2% is the tolerance used "
                          "throughout the flow measure."),
        "join": {
            "groups": split[0],
            "at_or_below": split[1],
            "above_within_tolerance": split[2],
            "above": split[3],
        },
        "coverage": cov,
        "diagnostic_all_phases": {
            "warning": ("Draft and realised summed together. This is not an appropriation and must not be used as a "
                        "comparator; it is kept only so the superseded figures stay traceable."),
            "overshoot_groups": len(all_rows),
            "overshoot_k": round(sum(r[4] - r[3] for r in all_rows)),
            "coverage": cov_all,
        },
        "rbv_model": {
            "expenditure_rows": rbv[0],
            "blank_rows": rbv[1],
            "note": ("rbv_model reads like the instrument classification that would bridge the two vocabularies and is "
                     "blank in every whole-row-distinct expenditure row, so the bridge must come from outside this "
                     "store. The column holds no NULLs; the blank is the empty string."),
        },
        "by_class": by_class,
        "groups": rows,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)} on the {BASIS} basis: {len(rows)} groups")
    print(f"  join: {split[0]} = {split[1]} at or below, {split[2]} above within 2%, {split[3]} above")
    for k, v in by_class.items():
        print(f"  {k:<22}{v['groups']:>3} groups  {v['overshoot_k']/1000:>9,.1f} M")
    print(f"  coverage: joinable {cov['joinable_share']:.1%}, policy {cov['other_policy_share']:.1%}, "
          f"blank/0 {cov['blank_or_zero_share']:.2%}")
    print(f"  all-phase diagnostic: {len(all_rows)} groups, "
          f"{payload['diagnostic_all_phases']['overshoot_k']/1000:,.1f} M (not a comparator)")
    print(f"  rbv_model blank: {rbv[1]} of {rbv[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
