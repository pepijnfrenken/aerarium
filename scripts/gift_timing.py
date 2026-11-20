#!/usr/bin/env python3
"""Gift timing: when did the money arrive, relative to the elections.

Income alone says nothing about whether a party was funded for a campaign or funded in general. Every gift row
carries a payment date, so the question is measurable: what share of a year's contributions landed inside the
campaign window before a Tweede Kamer election?

The window is a choice, and a choice with one value is a thumb on the scale. So the window is computed at 30,
60, 90 and 120 days and all four are reported. 90 days is the headline; the others show whether the finding
survives the choice. Nothing here is inferred: a row is in or out by its own date.

Elections: 2021-03-17, 2023-11-22, 2025-10-29. The gift data covers 2022-2024, so only 2023-11-22 falls inside
it. 2022 and 2024 are used as the same-calendar comparison, because a spring campaign and an autumn campaign
pull different months into the window.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "out" / "gifts_donors.csv"
OUT = REPO / "out" / "gift-timing.json"

ELECTIONS = [date(2021, 3, 17), date(2023, 11, 22), date(2025, 10, 29)]
WINDOWS = (30, 60, 90, 120)
HEADLINE = 90


def main() -> int:
    rows = [r for r in csv.DictReader(SRC.open(encoding="utf-8")) if r["kind"] == "contribution"]
    dated = []
    for r in rows:
        if not r["datum"] or not r["bedrag_gt_1000"]:
            continue
        try:
            d = date.fromisoformat(r["datum"])
            amt = float(r["bedrag_gt_1000"])
        except ValueError:
            continue
        dated.append((d, r["partij"], amt, r["donor"] or ""))

    print(f"dated contributions: {len(dated)} of {len(rows)} rows")
    print(f"total dated money: EUR {sum(a for _, _, a, _ in dated):,.2f}")

    monthly: dict[str, float] = defaultdict(float)
    for d, _, amt, _ in dated:
        monthly[f"{d.year}-{d.month:02d}"] += amt

    per_year = defaultdict(float)
    for d, _, amt, _ in dated:
        per_year[d.year] += amt

    # --- window analysis per election, per window length -------------------------
    windows = []
    for election in ELECTIONS:
        entry = {"election": election.isoformat(), "by_days": {}}
        for days in WINDOWS:
            start = election - timedelta(days=days)
            inside = sum(a for d, _, a, _ in dated if start <= d <= election)
            # same calendar window one year earlier and one year later, where data exists
            prev = sum(a for d, _, a, _ in dated
                       if start.replace(year=start.year - 1) <= d <= election.replace(year=election.year - 1))
            nxt = sum(a for d, _, a, _ in dated
                      if start.replace(year=start.year + 1) <= d <= election.replace(year=election.year + 1))
            entry["by_days"][days] = {
                "from": start.isoformat(), "to": election.isoformat(),
                "inside_eur": round(inside, 2),
                "same_window_year_before": round(prev, 2) or None,
                "same_window_year_after": round(nxt, 2) or None,
            }
        windows.append(entry)

    # --- per party, headline window, inside vs its own year ---------------------
    e2023 = date(2023, 11, 22)
    start = e2023 - timedelta(days=HEADLINE)
    party = defaultdict(lambda: {"in_window": 0.0, "year_2023": 0.0, "year_2022": 0.0, "year_2024": 0.0})
    for d, p, amt, _ in dated:
        if start <= d <= e2023:
            party[p]["in_window"] += amt
        if d.year == 2023:
            party[p]["year_2023"] += amt
        elif d.year == 2022:
            party[p]["year_2022"] += amt
        elif d.year == 2024:
            party[p]["year_2024"] += amt

    # How much of each party's money is even dated. A window share computed on a small dated base is not
    # comparable with one computed on most of the party's money, so the base is carried with every share.
    totals_by_party = defaultdict(float)
    totals_2023 = defaultdict(float)
    for r in csv.DictReader(SRC.open(encoding="utf-8")):
        if r["kind"] == "donor-total":
            totals_by_party[r["partij"]] += float(r["totaal"] or 0)
            # A ratio needs its denominator at the same period as its numerator. Dating a 2023 subset
            # against a three-year total is not a 2023 coverage figure, and naming it one made it wrong.
            if str(r.get("jaar", "")).strip() == "2023":
                totals_2023[r["partij"]] += float(r["totaal"] or 0)

    per_party = []
    for p, v in party.items():
        if v["year_2023"] <= 0:
            continue
        dated_2023 = v["year_2023"]
        all_years = totals_by_party.get(p, 0.0)
        only_2023 = totals_2023.get(p, 0.0)
        v["coverage"] = round(100 * dated_2023 / all_years, 1) if all_years else None
        v["coverage_2023"] = round(100 * dated_2023 / only_2023, 1) if only_2023 else None
        per_party.append({
            "partij": p,
            "in_window": round(v["in_window"], 2),
            "year_2023": round(v["year_2023"], 2),
            "share_of_2023_in_window": round(100 * v["in_window"] / v["year_2023"], 1),
            "year_2022": round(v["year_2022"], 2) or None,
            "year_2024": round(v["year_2024"], 2) or None,
            "dated_share_of_all_years": v.get("coverage"),
            "dated_share_of_2023": v.get("coverage_2023"),
        })
    per_party.sort(key=lambda x: -x["in_window"])

    total_in = sum(v["in_window"] for v in party.values())
    total_23 = sum(v["year_2023"] for v in party.values())
    total_all = sum(totals_by_party.values())
    print(f"\ncoverage: dated rows carry EUR {sum(a for _, _, a, _ in dated):,.2f} "
          f"of EUR {total_all:,.2f} in donor totals = {100*sum(a for _, _, a, _ in dated)/total_all:.1f}%")

    out = {
        "meta": {
            "source": "out/gifts_donors.csv (dashboard donor rows, kind=contribution)",
            "dated_rows": len(dated),
            "total_dated_eur": round(sum(a for _, _, a, _ in dated), 2),
            "window_choice": f"{HEADLINE} days before election day, chosen by hand; 30/60/90/120 all reported",
            "elections_in_window": ["2023-11-22"],
            "note": ("A gift dated inside a campaign window is not proof it was campaign money: the register "
                     "records a payment date, not a purpose. The comparison against 2022 and 2024 exists to stop "
                     "a seasonal pattern from being read as an election effect."),
        },
        "per_year_eur": {str(k): round(v, 2) for k, v in sorted(per_year.items())},
        "monthly_eur": {k: round(v, 2) for k, v in sorted(monthly.items())},
        "windows": windows,
        "per_party_2023": per_party,
        "totals_2023": {"in_window": round(total_in, 2), "year": round(total_23, 2),
                        "share": round(100 * total_in / total_23, 1) if total_23 else None},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nwrote {OUT} ({OUT.stat().st_size:,} bytes)")
    print("per year:", out["per_year_eur"])
    print(f"\n2023 election window ({start} .. {e2023}):")
    for days in WINDOWS:
        w = windows[1]["by_days"][days]
        print(f"  {days:>3}d  inside {w['inside_eur']:>14,.2f}   year-before {str(w['same_window_year_before']):>14}"
              f"   year-after {str(w['same_window_year_after']):>14}")
    print(f"\n2023 total {total_23:,.2f}; inside 90d {total_in:,.2f} = {out['totals_2023']['share']}%")
    print("\ntop parties by money inside the window:")
    for p in per_party[:8]:
        print(f"  {p['partij']:<7} window {p['in_window']:>12,.2f}  of 2023 {p['year_2023']:>12,.2f}"
              f"  = {p['share_of_2023_in_window']:>5.1f}%   2022 {p['year_2022'] or 0:>12,.0f}"
              f"  2024 {p['year_2024'] or 0:>12,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
