#!/usr/bin/env python3
"""Emit every chapter x instrument-type overshoot, classified, with the numbers behind the classification.

Why an artifact rather than a paragraph: FINDING-009 groups 42 overshoots into three classes, and a reader who
wants to disagree with the grouping needs the rows. Each group carries its own delta, the size of the chapter's
transfer line on both sides, and the class it was assigned. The class is an interpretation; the deltas are the
measurement, and both travel together so the second can be checked without accepting the first.

Classes:
  outside-appropriation  the instrument is financed by premiums or social funds, so the appropriation line is
                         symbolic (FINDING-008): Bekostiging, Bijdrage aan sociale fondsen.
  transfer-structure     the chapter routes money to another chapter, so its transfer line carries an
                         appropriation with no recipient row while the payment lands on the receiving instrument.
  unexplained            no transfer offset on either side; a candidate for a booking difference or a collision.
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


def main() -> int:
    con = duckdb.connect(DB, read_only=True)
    try:
        groups = con.execute("""
            with b as (select jaar, hoofdstuk_nummer as h, instrument_naam as i, sum(bedrag_k) as bud
                       from budget_line where vuo='U' group by 1,2,3),
                 r as (select jaar, hoofdstuk as h, instrument as i, sum(bedrag_k) as rec
                       from recipient_line group by 1,2,3)
            select b.jaar, b.h, b.i, b.bud, r.rec
            from b join r using (jaar, h, i)
            where r.rec > b.bud * 1.02
            order by (r.rec - b.bud) desc
        """).fetchall()

        rows = []
        for jaar, ch, inst, bud, rec in groups:
            tb, tr = con.execute("""
                select
                  (select coalesce(sum(bedrag_k), 0) from budget_line
                    where vuo='U' and jaar=? and hoofdstuk_nummer=? and instrument_naam=?),
                  (select coalesce(sum(bedrag_k), 0) from recipient_line
                    where jaar=? and hoofdstuk=? and instrument=?)""",
                [jaar, ch, TRANSFER, jaar, ch, TRANSFER]).fetchone()
            if inst in OUTSIDE:
                cls = "outside-appropriation"
            elif tb > 0:
                cls = "transfer-structure"
            else:
                cls = "unexplained"
            rows.append({
                "jaar": jaar, "chapter": ch, "instrument": inst,
                "budget_k": round(bud), "register_k": round(rec), "overshoot_k": round(rec - bud),
                "transfer_budget_k": round(tb), "transfer_register_k": round(tr),
                "class": cls,
            })

        cov = con.execute("""
            with ty as (select distinct instrument from recipient_line where instrument is not null),
                 b as (select instrument_naam as i, sum(bedrag_k) as s
                       from (select distinct * from budget_line) where vuo='U' group by 1)
            select
              coalesce(sum(case when b.i is not null and b.i<>''
                        and exists(select 1 from ty where ty.instrument=b.i) then b.s end),0),
              coalesce(sum(case when b.i is null or b.i='' or b.i='0' then b.s end),0),
              coalesce(sum(case when b.i is not null and b.i<>'' and b.i<>'0'
                        and not exists(select 1 from ty where ty.instrument=b.i) then b.s end),0),
              sum(b.s)
            from b""").fetchone()

        rbv = con.execute("select count(*) from (select distinct * from budget_line) where vuo='U'").fetchone()[0]
        rbv_blank = con.execute(
            "select count(*) from (select distinct * from budget_line) where vuo='U' and coalesce(rbv_model,'')=''"
        ).fetchone()[0]
    finally:
        con.close()

    by_class: dict[str, dict] = {}
    for r in rows:
        c = by_class.setdefault(r["class"], {"groups": 0, "overshoot_k": 0})
        c["groups"] += 1
        c["overshoot_k"] += r["overshoot_k"]

    payload = {
        "generated_by": "scripts/overshoots.py",
        "definition": ("A group is one (year, chapter, instrument type) where the recipient register records more "
                       "money than the appropriation carries, by more than 2%."),
        "why_2_percent": ("Rounding and re-publication move a line by small amounts; 2% is the tolerance used "
                          "throughout the flow measure, so a group here is outside it rather than near it."),
        "coverage": {
            "expenditure_total_k": round(cov[3]),
            "joinable_k": round(cov[0]),
            "joinable_share": round(cov[0] / cov[3], 4),
            "blank_or_zero_label_k": round(cov[1]),
            "other_policy_label_k": round(cov[2]),
            "other_policy_share": round(cov[2] / cov[3], 4),
            "note": ("Only the joinable share can be compared across the two registers. The rest is labelled with "
                     "policy instrument names the register never prints, so no recipient row can sit under it; "
                     "that is a naming difference, not a failure to disclose."),
        },
        "rbv_model": {
            "expenditure_rows": rbv,
            "blank_rows": rbv_blank,
            "note": ("rbv_model reads like the instrument classification that would bridge the two vocabularies "
                     "and is blank in every row, so the bridge must come from outside this store."),
        },
        "by_class": by_class,
        "groups": rows,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}: {len(rows)} groups")
    for k, v in by_class.items():
        print(f"  {k:<22}{v['groups']:>3} groups  {v['overshoot_k']/1000:>9,.1f} M")
    print(f"  joinable share of expenditure: {payload['coverage']['joinable_share']:.1%}")
    print(f"  rbv_model blank: {rbv_blank} of {rbv} expenditure rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
