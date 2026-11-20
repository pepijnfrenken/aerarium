#!/usr/bin/env python3
"""Pull the campaign-spend line out of each party's annual report, with the ambiguity left visible.

Income is easy: the register publishes a number. Spending is not. Each party lays out its own statement, and the
campaign line appears in at least three shapes:

    VVD 2023   Verkiezingscampagne      22 1.050.000 4.675.900 3.790.634
    GL  2023   I. Activiteiten ... campagne    E 836.285     EUR 2.861.445
    several    verkiezingscampagne                                  2.861.445

The first has three amounts (budget for this year, actual for this year, actual for last year, plus a note
number), the second has two (budget, actual), the third has one. There is no cross-party convention, so a script
that picks "the last number" silently mixes years and mixes budget with actual.

So this script does not pick. It records every amount on the line, the line as evidence, and a quality flag:

    pair      exactly two amounts -> begroot, werkelijk. `value` = the second, declared below.
    single    one amount -> that amount, but it is not stated whether budget or actual.
    ambiguous three or more -> no value assigned, all amounts kept.

The declared rule for `pair` is that the last amount is the realised figure, which is the layout both CDA and GL
use. It is a rule, not a fact about the document, and any figure derived from it carries that label.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "corpus" / "text"
OUT = REPO / "out" / "spending-campaign.csv"
FIELDS = ["partij", "jaar", "bestand", "label", "amounts", "n_amounts", "quality", "value_eur", "raw_line"]

# euro amounts as Dutch reports print them: 1.050.000 or 836.285 or 2.861.445,50
AMOUNT = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d{2})?")
LABELS = ("verkiezingscampagne", "verkiezingscampagn")


def parse_amount(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def main() -> int:
    files = sorted(CORPUS.glob("*.txt"))
    if not files:
        print(f"no corpus at {CORPUS}", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for f in files:
        # filename: <year>_<party>_<deel>_<hash>.txt
        parts = f.stem.split("_")
        jaar = parts[0] if parts[0].isdigit() else ""
        partij = parts[1] if len(parts) > 1 else ""

        seen = set()
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            low = line.lower()
            if not any(k in low for k in LABELS):
                continue
            # skip table-of-contents rows: they end in a page number and carry a dot leader
            if "...." in line:
                continue
            amounts = AMOUNT.findall(line)
            # a single bare year or a page reference is not money
            amounts = [a for a in amounts if parse_amount(a) >= 1000]
            if not amounts:
                continue
            key = tuple(amounts)
            if key in seen:
                continue
            seen.add(key)

            n = len(amounts)
            quality = "pair" if n == 2 else ("single" if n == 1 else "ambiguous")
            value = parse_amount(amounts[1]) if n == 2 else (parse_amount(amounts[0]) if n == 1 else None)
            rows.append({
                "partij": partij, "jaar": jaar, "bestand": f.name,
                "label": "verkiezingscampagne", "amounts": " | ".join(amounts), "n_amounts": n,
                "quality": quality,
                "value_eur": f"{value:.2f}" if value is not None else "",
                "raw_line": " ".join(line.split())[:220],
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    by_q: dict[str, int] = {}
    for r in rows:
        by_q[r["quality"]] = by_q.get(r["quality"], 0) + 1

    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes), {len(rows)} campaign lines from {len(files)} reports")
    print(f"quality: {by_q}")
    pairs = [r for r in rows if r["quality"] == "pair"]
    print(f"\n{pairs.__len__()} party-years with an unambiguous begroot/werkelijk pair:")
    for r in sorted(pairs, key=lambda r: -float(r["value_eur"]))[:10]:
        print(f"  {r['jaar']} {r['partij']:<6} {r['amounts']:<28} -> realised EUR {float(r['value_eur']):,.2f}")
    amb = [r for r in rows if r["quality"] == "ambiguous"]
    if amb:
        print(f"\n{len(amb)} left ambiguous, example:")
        for r in amb[:3]:
            print(f"  {r['jaar']} {r['partij']:<6} {r['amounts'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
