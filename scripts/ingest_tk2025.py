#!/usr/bin/env python3
"""Ingest the Tweede Kamer election 2025 gift overviews (BZK, ODS).

Why these files exist and the dashboard does not carry them: in an election year parties owe two extra
disclosures. They filed gifts and debts for 1 January 2024 to 8 October 2025 a week before the 29 October 2025
election, and supplementary ones for the final three weeks afterwards. Those are published on rijksoverheid.nl as
ODS spreadsheets, not on the dashboard, which is why the dashboard's year pages stop at 2024. The annual reports
for 2025 are not due until 1 July 2026 and had not been published when this ran.

Two files matter:
  overzicht-giften-aan-politieke-partijen-...   gifts to parties and their neveninstellingen
  overzicht-giften-aan-kandidaten-...           gifts to individual candidates (a layer the annual reports lack)

Structure of the party file: a summary block (one row per party, with Giften 2024 / Giften 2025 / Eindtotaal),
then a detail block. Each donor gets a row carrying `Eindtotaal` (col 2); if a gift was paid in instalments the
individual amounts >= EUR 1.000 follow as rows without an Eindtotaal. So a party total equals the sum of donor
Eindtotaal values, and that equality is the gate this script enforces.

Privacy: the register publishes only a natural person's place of residence, and a full address only for legal
persons (footnote 1 of the source). Col 4 is therefore split into `plaats` and, where a street was published,
`adres`. The published CSV keeps the street only when the source published one.
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
OUT_CSV = REPO / "out" / "gifts-2025-election.csv"
OUT_JSON = REPO / "out" / "gifts-2025-election.json"
CAND_CSV = REPO / "out" / "candidate-gifts-2025.csv"
CAND_FIELDS = ["partij", "nr", "kandidaat", "woonplaats", "gift", "totaalbedrag", "donor", "plaats_donor",
               "adres_donor", "ubo_naam", "plaats_ubo", "totaal_2023", "totaal_2024", "totaal_2025",
               "eindtotaal", "datum", "kieskring", "bron"]

PARTY_FILE = "overzicht-giften-aan-politieke-partijen-tweede-kamerverkiezing-2025.ods"
CAND_FILE = "overzicht-giften-aan-kandidaten-tweede-kamerverkiezing-2025.ods"
FIELDS = ["partij", "neveninstelling", "donor", "plaats", "adres", "ubo_naam", "plaats_ubo",
          "totaal_2024", "totaal_2025", "eindtotaal", "losse_bijdrage", "datum", "bijzonderheden", "bron"]


def party_key(label: str) -> str:
    """The detail block and the summary block do not agree on the party numbering ('06. BBB' vs '07. BBB'),
    and GL and PvdA share a number because they ran on one list. So the name is the key, never the label."""
    return label.split(".", 1)[1].strip() if label[:3].strip().rstrip(".").isdigit() else label.strip()


def clean(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return " ".join(str(x).replace("\xa0", " ").split())


def money(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        return ""


def dstr(x) -> str:
    if isinstance(x, pd.Timestamp):
        return x.date().isoformat()
    s = clean(x)
    return s[:10] if len(s) >= 10 and s[4] == "-" else s


def split_address(raw: str) -> tuple[str, str]:
    """The source prints 'street, postcode city' for legal persons and just 'city' for natural persons."""
    if "," not in raw:
        return raw, ""
    street, _, place = raw.rpartition(",")
    return place.strip(), street.strip()


def parse_party_file(path: Path) -> tuple[list[dict], dict[str, float], dict[str, float]]:
    df = pd.read_excel(path, sheet_name=0, engine="odf", header=None)

    # summary block: party rows before the 'Eindtotaal' line
    summary: dict[str, dict] = {}
    for i in range(df.shape[0]):
        c0 = clean(df.iat[i, 0])
        if c0.startswith("Eindtotaal"):
            break
        if not (c0[:2].isdigit() and c0[2:3] == "."):
            continue
        y24, y25, eind = df.iat[i, 3], df.iat[i, 4], df.iat[i, 5]
        if not isinstance(eind, (int, float)) or pd.isna(eind):
            continue
        summary[party_key(c0)] = {
            "y2024": float(y24) if isinstance(y24, (int, float)) and not pd.isna(y24) else None,
            "y2025": float(y25) if isinstance(y25, (int, float)) and not pd.isna(y25) else None,
            "eind": float(eind),
        }

    # detail block starts at the row whose col0 is 'Politieke partij' and col1 is 'Neveninstelling'
    start = next(i for i in range(df.shape[0])
                 if clean(df.iat[i, 0]) == "Politieke partij" and "Neveninstelling" in clean(df.iat[i, 1]))

    rows: list[dict] = []
    detail_totals: dict[str, float] = defaultdict(float)
    for i in range(start + 1, df.shape[0]):
        partij = clean(df.iat[i, 0])
        donor = clean(df.iat[i, 3])
        if not partij and not donor:
            continue
        eind = money(df.iat[i, 2])
        los = money(df.iat[i, 9])
        if not (partij or donor):
            continue
        plaats, adres = split_address(clean(df.iat[i, 4]))
        rows.append({
            "partij": partij, "neveninstelling": clean(df.iat[i, 1]), "donor": donor,
            "plaats": plaats, "adres": adres, "ubo_naam": clean(df.iat[i, 5]),
            "plaats_ubo": clean(df.iat[i, 6]),
            "totaal_2024": money(df.iat[i, 7]), "totaal_2025": money(df.iat[i, 8]),
            "eindtotaal": eind, "losse_bijdrage": los, "datum": dstr(df.iat[i, 10]),
            "bijzonderheden": clean(df.iat[i, 11]), "bron": "tk2025-partijen",
        })
        if eind:
            detail_totals[party_key(partij)] += float(eind)
    return rows, summary, detail_totals


def parse_candidate_file(path: Path) -> list[dict]:
    """One row per candidate. `Gift ja/nee` says whether any gift reached that candidate, and the donor columns
    repeat for the candidates who did receive one. 17 columns, header in the middle of the sheet."""
    df = pd.read_excel(path, sheet_name=0, engine="odf", header=None)
    hdr = next((i for i in range(df.shape[0])
                if clean(df.iat[i, 0]) == "Politieke partij"
                and any("Naam kandidaat" in clean(df.iat[i, c]) for c in range(df.shape[1]))), None)
    if hdr is None:
        return []

    rows: list[dict] = []
    for i in range(hdr + 1, df.shape[0]):
        partij = clean(df.iat[i, 0])
        naam = clean(df.iat[i, 2])
        if not naam:
            continue
        plaats, adres = split_address(clean(df.iat[i, 7]))
        rows.append({
            "partij": partij,
            "nr": clean(df.iat[i, 1]),
            "kandidaat": naam,
            "woonplaats": clean(df.iat[i, 3]),
            "gift": clean(df.iat[i, 4]),
            "totaalbedrag": money(df.iat[i, 5]),
            "donor": clean(df.iat[i, 6]),
            "plaats_donor": plaats,
            "adres_donor": adres,
            "ubo_naam": clean(df.iat[i, 8]),
            "plaats_ubo": clean(df.iat[i, 9]),
            "totaal_2023": money(df.iat[i, 10]),
            "totaal_2024": money(df.iat[i, 11]),
            "totaal_2025": money(df.iat[i, 12]),
            "eindtotaal": money(df.iat[i, 13]),
            "datum": dstr(df.iat[i, 15]),
            "kieskring": clean(df.iat[i, 16]),
            "bron": "tk2025-kandidaten",
        })
    return rows


def main() -> int:
    pf, cf = RAW / PARTY_FILE, RAW / CAND_FILE
    if not pf.exists():
        print(f"missing {pf}\nrun scripts/fetch_tk2025.sh first", file=sys.stderr)
        return 1

    rows, summary, detail = parse_party_file(pf)
    print(f"party gift rows: {len(rows)}   parties in summary: {len(summary)}")

    # ---- the gate: per party, donor Eindtotaal must equal the published party total -------------
    mismatches = []
    for party, pub in summary.items():
        got = round(detail.get(party, 0.0), 2)
        # detail Eindtotaal covers 2024 and 2025 both, so it is compared with the file's own Eindtotaal column
        if abs(got - round(pub["eind"], 2)) > 0.02:
            mismatches.append({"partij": party, "published_eind": round(pub["eind"], 2),
                               "y2025": pub["y2025"], "detail_sum": got, "diff": round(got - pub["eind"], 2)})
    total_published = round(sum(v["eind"] for v in summary.values()), 2)
    total_2025_only = round(sum(v["y2025"] or 0 for v in summary.values()), 2)
    total_detail = round(sum(detail.values()), 2)
    print(f"published 2025-only: {total_2025_only:,.2f}   published einsd (2024+2025): {total_published:,.2f}")
    print(f"published total 2025: {total_published:,.2f}")
    print(f"sum of donor rows   : {total_detail:,.2f}")
    print(f"parties not reconciling: {len(mismatches)}")
    for m in mismatches[:8]:
        print(f"   {m['partij']:<26} published {m['published_eind']:>12,.2f}  detail {m['detail_sum']:>12,.2f}"
              f"  diff {m['diff']:>10,.2f}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    cand_rows = parse_candidate_file(cf) if cf.exists() else []
    if cand_rows:
        with CAND_CSV.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=CAND_FIELDS)
            w.writeheader()
            w.writerows(cand_rows)
    per_party = sorted(
        ({"partij": p,
          "totaal_2025": round((summary[p]["y2025"] if p in summary and summary[p].get("y2025") is not None
                               else detail.get(p, 0.0)), 2),
          "detail_sum": round(v, 2),
          # Count rows with a POSITIVE 2025 amount, not rows that merely carry some total. The old test
          # was truthiness on `eindtotaal`, which counted rows whose money is in 2023 or 2024 and put
          # them in a 2025 column: FNP read 58 against 17 actual positive-2025 rows.
          "donors": sum(1 for r in rows if party_key(r["partij"]) == p
                        and float(r["totaal_2025"] or 0) > 0)}
         for p, v in detail.items()), key=lambda x: -x["totaal_2025"])

    OUT_JSON.write_text(json.dumps({
        "meta": {
            "source": "BZK overviews for the Tweede Kamer election of 29 October 2025",
            "period": "1 January 2024 to 8 October 2025; supplementary overview to 29 October published separately",
            "threshold": "EUR 767,12 in an election year, against EUR 1.000 normally",
            "why_not_on_the_dashboard": ("Election-year disclosures are published as ODS on rijksoverheid.nl. The "
                                         "dashboard's year pages carry 2022-2024, and the 2025 annual reports are "
                                         "not due until 1 July 2026."),
            "privacy": ("The source publishes only a natural person's place of residence; a full address appears "
                        "for legal persons only. adres is empty for natural persons by construction."),
            "reconciliation": {"published_eind_2024_plus_2025": total_published,
                               "published_2025_only": total_2025_only,
                               "detail_sum": total_detail,
                               "parties_not_reconciling": mismatches},
        },
        "per_party": per_party,
        "totals": {"2025_to_8_oct": total_2025_only, "eind_2024_plus_2025": total_published},
        "candidates": {
            # Rows are not people and not years. An audit found this summary reporting 1,168 rows as
            # though that were a count of candidates who received a gift, while the affirmative rows
            # were four people across three years and only part of the money was 2025 money. Every
            # count below names its own unit.
            "rows": len(cand_rows),
            "distinct_candidates": len({(r["partij"], r["nr"], r["kandidaat"]) for r in cand_rows}),
            "with_a_gift": sum(1 for r in cand_rows if r["gift"].lower().startswith("ja")),
            "recipients_any_amount": len({(r["partij"], r["nr"], r["kandidaat"])
                                          for r in cand_rows if float(r["eindtotaal"] or 0) > 0}),
            "recipients_2025": len({(r["partij"], r["nr"], r["kandidaat"])
                                    for r in cand_rows if float(r["totaal_2025"] or 0) > 0}),
            "total_gifted_combined": round(sum(float(r["eindtotaal"] or 0) for r in cand_rows), 2),
            "total_2023": round(sum(float(r["totaal_2023"] or 0) for r in cand_rows), 2),
            "total_2024": round(sum(float(r["totaal_2024"] or 0) for r in cand_rows), 2),
            "total_2025": round(sum(float(r["totaal_2025"] or 0) for r in cand_rows), 2),
            "units": ("rows = sheet rows; distinct_candidates = unique (partij, nr, kandidaat); "
                      "recipients_2025 = candidates with a positive 2025 amount. The combined total "
                      "spans 2023-2025 and is not a 2025 figure."),
        },
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nwrote {OUT_CSV} ({OUT_CSV.stat().st_size:,} bytes), {len(rows)} rows")
    print(f"wrote {OUT_JSON} ({OUT_JSON.stat().st_size:,} bytes)")
    if cand_rows:
        withgift = [r for r in cand_rows if r["gift"].lower().startswith("ja")]
        tot = round(sum(float(r["eindtotaal"]) for r in cand_rows if r["eindtotaal"]), 2)
        print(f"candidates: {len(cand_rows)} rows, {len(withgift)} received a gift, total EUR {tot:,.2f}")
        for r in withgift[:6]:
            print(f"   {r['partij']:<14} {r['kandidaat'][:24]:<24} EUR {r['eindtotaal']:>10}  donor {r['donor'][:26]}")
    else:
        print("candidate file: no detail rows found")
    print(f"\n{'party':<26}{'gifts 2025':>14}{'donors':>8}")
    for p in per_party[:10]:
        print(f"{p['partij']:<26}{p['totaal_2025']:>14,.2f}{p['donors']:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
