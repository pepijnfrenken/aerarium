#!/usr/bin/env python3
"""Assemble the state-side payload the page renders.

The ledger page is self-contained: it makes no network requests and works from `file://`, so anything it draws has
to travel inside the HTML. The existing payload is `view-data.json` (the party side). This writes a second,
separate payload for the state side, drawing only on artifacts that already carry a gate:

  out/govrun.json       what a ministry spends, on the expenditure axis
  out/overshoots.json   every chapter x instrument overshoot and its class
  out/rekenkamer.json   the rung-6 publication register

Nothing here is recomputed from the store, and nothing is typed in by hand: every figure is read from the artifact
that records it, so a correction upstream moves the page. Where an artifact says a thing is unmeasured (no PDF
text read), that state is carried through as `null` rather than as a zero.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "out"


def load(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def main() -> int:
    gov = load("govrun.json")
    ovr = load("overshoots.json")
    rk = load("rekenkamer.json")

    national = gov.get("national", {})
    per_chapter = gov.get("per_chapter", [])
    # Largest chapters by programme spending, which is the comparable figure: a chapter total still carries
    # receipts, financial transactions and transfers to other chapters.
    ranked = sorted(
        [c for c in per_chapter if (c.get("expenditure_k") or 0) > 0],
        key=lambda c: c.get("expenditure_k") or 0, reverse=True,
    )[:8]

    cov = ovr["coverage"]
    cls = ovr["by_class"]
    rk_counts = rk["counts"]
    rk_cov = rk["coverage"]

    payload = {
        "generated_by": "scripts/build_state_payload.py",
        "year": gov.get("year"),
        "unit": "EUR thousand",
        "spend": {
            "expenditure_axis_k": national.get("expenditure_axis_k"),
            "programme_k": national.get("expenditure_k"),
            "financial_k": national.get("financial_k"),
            "interchapter_k": national.get("inter_chapter_k"),
            "personnel_k": national.get("personnel_k"),
            "note": ("Expenditure axis only (vuo='U'), less financial transactions and inter-chapter transfers. "
                     "A chapter total is not spending: it also carries receipts and loans."),
            "ranked_chapters": [
                {"chapter": c.get("chapter"), "name": c.get("name"), "spending_k": c.get("expenditure_k")}
                for c in ranked
            ],
        },
        "join": {
            "joinable_k": cov["joinable_k"],
            "joinable_share": cov["joinable_share"],
            "other_policy_k": cov["other_policy_label_k"],
            "other_policy_share": cov["other_policy_share"],
            "total_k": cov["expenditure_total_k"],
            "screens": ovr.get("screens"),
            "rbv_blank_rows": ovr["rbv_model"]["blank_rows"],
            "rbv_rows": ovr["rbv_model"]["expenditure_rows"],
            "classes": {k: {"groups": v["groups"], "overshoot_k": v["overshoot_k"]} for k, v in cls.items()},
            "groups_total": len(ovr["groups"]),
            "note": ("Only the joinable share can be compared across the two registers. The rest is labelled with "
                     "policy instrument names the recipient register never prints, so no recipient row can sit "
                     "under it: a naming difference, not a failure to disclose."),
        },
        "outside": {
            "groups": cls.get("outside-appropriation", {}).get("groups"),
            "overshoot_k": cls.get("outside-appropriation", {}).get("overshoot_k"),
            "rows": [
                g for g in ovr["groups"] if g["class"] == "outside-appropriation"
            ][:6],
            "note": ("Premium- and fund-financed flows. They reach a named recipient but were never appropriated, "
                     "so they do not satisfy the chain from rung 1. The mechanism for the social funds is inferred "
                     "from the mismatch and the statutory financing; the arithmetic is measured."),
        },
        "rekenkamer": {
            "pages": rk_cov.get("pages_harvested"),
            "pages_in_scope": rk_cov.get("pages_in_scope"),
            "harvest_complete": rk_cov.get("harvest_complete"),
            "attached_by_title": rk_counts.get("attached_by_title"),
            "findings": rk_counts.get("attached_by_title_and_a_finding"),
            "by_kind": rk.get("by_kind"),
            "by_chapter": dict(list(rk.get("by_chapter", {}).items())[:10]),
            # null, never 0: no PDF was downloaded, so no body text was read.
            "body_matches": None,
            "note": ("A publication is attached to a chapter only when its own title names that ministry. The "
                     "register also carries ministries' reactions, answers and covering briefs, which are counted "
                     "but not treated as findings. No PDF has been read, so the body-match count is unmeasured."),
        },
    }
    (OUT / "state-data.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")

    print("wrote out/state-data.json")
    print(f"  year {payload['year']}: expenditure axis {payload['spend']['expenditure_axis_k']:,} k, "
          f"programme {payload['spend']['programme_k']:,} k")
    print(f"  joinable {payload['join']['joinable_share']:.1%} of expenditure; "
          f"{payload['join']['rbv_blank_rows']:,}/{payload['join']['rbv_rows']:,} rbv_model blank")
    print(f"  outside the appropriation: {payload['outside']['groups']} groups, "
          f"{payload['outside']['overshoot_k']/1000:,.1f} M")
    print(f"  rekenkamer: {payload['rekenkamer']['pages']:,} pages, "
          f"{payload['rekenkamer']['attached_by_title']:,} attached, {payload['rekenkamer']['findings']:,} findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
