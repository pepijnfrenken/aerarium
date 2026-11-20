#!/usr/bin/env python3
"""Ingest the post-election and debt overviews for the Tweede Kamer election of 29 October 2025.

Three files, all ODS, all from BZK:

  post-giften.ods    gifts received in the final three weeks (9 to 29 October 2025), submitted by 29 November
                     2025 and published by 29 December 2025. This is the window the 22 October files cannot
                     cover, and the one that matters most for campaign timing: it is the last stretch before
                     the vote.
  post-schulden.ods  debts of EUR 25.000 or more after the election.
  overzicht-schulden-van-politieke-partijen-...ods (pre)  the same, before it.

Debt is context for gift flow, not a gift: a party that borrows to campaign is funded differently from one that
receives donations, and the two must never be added together. The output keeps them in separate objects.

Every file is party-level with a donor detail block underneath. The totals are asserted against the detail sum,
and a mismatch is reported rather than smoothed.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw" / "tk2025"
OUT_CSV = REPO / "out" / "gifts-2025-post-election.csv"
OUT_JSON = REPO / "out" / "debts-2025.json"

GIFT_FIELDS = ["partij", "donor", "plaats", "adres", "ubo_naam", "plaats_ubo", "bedrag", "datum", "bron"]


def clean(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return " ".join(str(x).replace("\xa0", " ").split())


def num(x) -> float | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def party_key(label: str) -> str:
    return label.split(".", 1)[1].strip() if label[:3].strip().rstrip(".").isdigit() else label.strip()


def split_address(raw: str) -> tuple[str, str]:
    if "," not in raw:
        return raw, ""
    street, _, place = raw.rpartition(",")
    return place.strip(), street.strip()


def parse_party_totals(path: Path, total_col: int) -> dict[str, float]:
    """Party rows before the 'Eindtotaal' line. Column layout differs between the gift and the debt files."""
    d = pd.read_excel(path, sheet_name=0, engine="odf", header=None)
    out: dict[str, float] = {}
    for i in range(d.shape[0]):
        c0 = clean(d.iat[i, 0])
        if c0.startswith("Eindtotaal") or c0.startswith("Toelichting"):
            break
        if not (c0[:2].isdigit() and c0[2:3] == "."):
            continue
        v = num(d.iat[i, total_col])
        if v is not None:
            out[party_key(c0)] = round(v, 2)
    return out


def parse_gift_detail(path: Path) -> list[dict]:
    d = pd.read_excel(path, sheet_name=0, engine="odf", header=None)
    hdr = next((i for i in range(d.shape[0])
                if clean(d.iat[i, 0]) == "Politieke partij"
                and any("Naam gever" in clean(d.iat[i, c]) for c in range(d.shape[1]))), None)
    if hdr is None:
        return []
    cols = {clean(d.iat[hdr, c]): c for c in range(d.shape[1])}
    rows: list[dict] = []
    for i in range(hdr + 1, d.shape[0]):
        partij, donor = clean(d.iat[i, cols.get("Politieke partij", 0)]), clean(d.iat[i, cols.get("Naam gever", 0)])
        if not donor:
            continue
        raw_addr = clean(d.iat[i, cols.get("Adres en woonplaats gever", 0)]) if "Adres en woonplaats gever" in cols else ""
        plaats, adres = split_address(raw_addr)
        datum = d.iat[i, cols["Datum"]] if "Datum" in cols else None
        rows.append({
            "partij": party_key(partij), "donor": donor, "plaats": plaats, "adres": adres,
            "ubo_naam": clean(d.iat[i, cols.get("Naam UBO", 0)]) if "Naam UBO" in cols else "",
            "plaats_ubo": clean(d.iat[i, cols.get("Woonplaats UBO", 0)]) if "Woonplaats UBO" in cols else "",
            "bedrag": (f"{num(d.iat[i, cols['Eindtotaal']]):.2f}"
                       if "Eindtotaal" in cols and num(d.iat[i, cols["Eindtotaal"]]) is not None else ""),
            "datum": datum.date().isoformat() if isinstance(datum, pd.Timestamp) else clean(datum)[:10],
            "bron": "tk2025-post-election",
        })
    return rows


def parse_creditors(path: Path, period: str) -> list[dict]:
    """Who is owed. The debt files carry a detail block per creditor; a creditor's own row holds the total and
    instalment rows follow without one, so only rows carrying an Eindtotaal are kept."""
    d = pd.read_excel(path, sheet_name=0, engine="odf", header=None)
    hdr = next((i for i in range(d.shape[0])
                if clean(d.iat[i, 0]) == "Politieke partij"
                and any("crediteur" in clean(d.iat[i, c]).lower() for c in range(d.shape[1]))), None)
    if hdr is None:
        return []
    cols = {clean(d.iat[hdr, c]): c for c in range(d.shape[1])}
    out: list[dict] = []
    for i in range(hdr + 1, d.shape[0]):
        cred = clean(d.iat[i, cols.get("Naam crediteur", 0)])
        amount = num(d.iat[i, cols.get("Eindtotaal", 2)])
        party = clean(d.iat[i, cols.get("Politieke partij", 0)])
        if not cred or amount is None or or_blank(party):
            continue
        out.append({"partij": party_key(party), "crediteur": cred, "bedrag": round(amount, 2),
                    "neveninstelling": clean(d.iat[i, cols.get("Neveninstelling", 1)]), "period": period})
    return out


def or_blank(v: str) -> bool:
    return v in ("", "nan", "None")


def main() -> int:
    gift_post = RAW / "post-giften.ods"
    debt_post = RAW / "post-schulden.ods"
    debt_pre = RAW / "overzicht-schulden-van-politieke-partijen-tweede-kamerverkiezing-2025.ods"
    for f in (gift_post, debt_post, debt_pre):
        if not f.exists():
            print(f"missing {f}", file=sys.stderr)
            return 1

    post_totals = parse_party_totals(gift_post, total_col=3)
    detail = parse_gift_detail(gift_post)

    detail_sum: dict[str, float] = defaultdict(float)
    for r in detail:
        if r["bedrag"]:
            detail_sum[r["partij"]] += float(r["bedrag"])
    mismatches = [{"partij": p, "published": v, "detail_sum": round(detail_sum.get(p, 0.0), 2)}
                  for p, v in post_totals.items() if abs(detail_sum.get(p, 0.0) - v) > 0.02]

    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=GIFT_FIELDS)
        w.writeheader()
        w.writerows(detail)

    debts_pre = parse_party_totals(debt_pre, total_col=5)
    debts_post = parse_party_totals(debt_post, total_col=3)
    creditors = (parse_creditors(debt_pre, "2024-01-01..2025-10-08")
                 + parse_creditors(debt_post, "2025-10-09..2025-10-29"))
    creditors.sort(key=lambda c: -c["bedrag"])

    parties = sorted(set(post_totals) | set(debts_pre) | set(debts_post))
    table = []
    for p in parties:
        table.append({
            "partij": p,
            "gifts_final_3_weeks": post_totals.get(p, 0.0),
            "debts_2024_to_8oct2025": debts_pre.get(p),
            "debts_9_to_29oct2025": debts_post.get(p),
        })

    OUT_JSON.write_text(json.dumps({
        "meta": {
            "source": "BZK overviews for the Tweede Kamer election of 29 October 2025",
            "post_election_period": "9 to 29 October 2025 (final three weeks before the vote)",
            "gift_threshold": "EUR 767,12, the election-year threshold",
            "debt_threshold": "EUR 25.000, and a short-term debt repaid within fourteen days need not be registered",
            "debt_periods": {
                "debts_2024_to_8oct2025": "1 January 2024 to 8 October 2025, a 22-month period",
                "debts_9_to_29oct2025": "9 to 29 October 2025, the final three weeks only",
                "warning": ("These two files cover DISJOINT periods, not a before and an after. Their totals are "
                            "not a delta and must never be subtracted: the first is 22 months of debt, the second "
                            "is three weeks of it."),
            },
            "warning": ("Gifts and debts are different flows and are never summed. A debt is borrowed money; a "
                        "gift is not repaid. Both are shown because a party that borrows to campaign is funded "
                        "by a different mechanism than one that receives donations."),
            "reconciliation": {"parties_not_reconciling": mismatches,
                               "gift_detail_sum": round(sum(detail_sum.values()), 2),
                               "gift_published_total": round(sum(post_totals.values()), 2)},
        },
        "gift_totals": {"published": round(sum(post_totals.values()), 2), "detail_rows": len(detail)},
        "per_party": sorted(table, key=lambda x: -x["gifts_final_3_weeks"]),
        "creditors": creditors[:60],
        "creditor_count": len(creditors),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"final three weeks: EUR {sum(post_totals.values()):,.2f} across {len(post_totals)} parties, "
          f"{len(detail)} donor rows, detail sum EUR {sum(detail_sum.values()):,.2f}")
    print(f"parties not reconciling: {len(mismatches)}")
    for m in mismatches[:6]:
        print(f"   {m['partij']:<22} published {m['published']:>12,.2f}  detail {m['detail_sum']:>12,.2f}")
    print(f"\ndebts 1 Jan 2024-8 Oct 2025 (22 months): EUR {sum(debts_pre.values()):,.2f} across {len(debts_pre)} parties")
    print(f"debts 9-29 Oct 2025 (3 weeks):            EUR {sum(debts_post.values()):,.2f} across {len(debts_post)} parties")
    print("   these are disjoint periods, not a before/after: not subtractable")
    print(f"creditor rows: {len(creditors)}; largest: "
          + ", ".join(f"{c['partij']} -> {c['crediteur'][:28]} {c['bedrag']:,.0f}" for c in creditors[:4]))
    print(f"\nwrote {OUT_CSV.name} ({OUT_CSV.stat().st_size:,} B) and {OUT_JSON.name} ({OUT_JSON.stat().st_size:,} B)")
    print(f"\n{'party':<22}{'gifts last 3wk':>17}{'debt 22mo':>16}{'debt 3wk':>15}")
    for r in table[:8]:
        print(f"{r['partij']:<22}{r['gifts_final_3_weeks']:>17,.2f}"
              f"{(r['debts_2024_to_8oct2025'] or 0):>16,.2f}{(r['debts_9_to_29oct2025'] or 0):>15,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
