#!/usr/bin/env python3
"""Classify the creditors a party owes, so media money can be separated from tax, staff and property.

What this measures, exactly: **debt outstanding to media and advertising suppliers at the disclosure date**, for
debts of EUR 25.000 or more. It is not media spend. A party that paid its media invoices on time appears here as
zero. A party that bought EUR 3M of advertising and had paid most of it appears as the remainder. So the figure is
a floor, and the only honest way to publish it is with that sentence attached.

It is still worth publishing: it is standardised, dated, thresholded and comparable across parties, which the
free-format annual reports are not (see FINDING-004). For the final three weeks before the 2025 election it is the
only comparable number that exists for campaign media money.

Classification is keyword-first and ordered. Anything that matches nothing lands in `unclassified` and is printed,
never silently dropped into another bucket.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "out" / "debts-2025.json"
OUT = REPO / "out" / "media-debt.json"

# ordered: first match wins
RULES: list[tuple[str, tuple[str, ...]]] = [
    ("tax", ("belastingdienst",)),
    ("pension", ("pensioenfonds", "abp ", "pno media")),
    ("staff", ("medewerkers vereniging", "stichting personeel", "personeel ")),
    ("own_entity", ("bureau de helling", "dwars", "international foundation", "volt europa",
                    "stichting wetenschappelijk", "renaissance instituut")),
    ("media", ("media", "reclame", "advert", "outdoor", "dpg", "nrc ", "stroom", "abovo", "cheil",
               "de media balie", "mediabureau", "mediacommunicatie", "acato", "growing minds",
               "digital", "online", "video", "drukkerij", "printing")),
    ("production_av", ("stagelight", "sound & vision", "heuvelman", "vormats", "av ", "licht", "geluid")),
    ("venue", ("ahoy", "nbc", "congrescentrum", "brabanthallen", "breepark", "postillion", "omnisport",
               "eventstudios", "platinastaete", "hotel", "convention")),
    ("property", ("bouw", "onroerend goed", "vastgoed", "installaties", "cbre", "wonen", "huur",
                  "vellinga", "hajofi")),
    ("professional_services", ("berenschot", "improve", "security & investigation", "bazelmans", "abf",
                               "accountant", "advies")),
]


def classify(name: str) -> str:
    # normalise: strip periods and collapse spaces, so "N.B.C. Exploitatie B.V." matches "nbc"
    low = " " + " ".join(name.lower().replace(".", " ").split()) + " "
    for label, keys in RULES:
        if any(k in low for k in keys):
            return label
    return "unclassified"


def main() -> int:
    if not SRC.exists():
        print(f"missing {SRC}; run scripts/ingest_tk2025_post.py first", file=sys.stderr)
        return 1
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    creditors = doc.get("creditors") or []

    by_cat: dict[str, float] = defaultdict(float)
    media_by_party: dict[str, dict] = {}
    unclassified: dict[str, float] = {}
    for c in creditors:
        cat = classify(c["crediteur"])
        by_cat[cat] += c["bedrag"]
        if cat == "media":
            slot = media_by_party.setdefault(c["partij"], {"partij": c["partij"], "media_eur": 0.0,
                                                           "creditors": [], "periods": set(),
                                                           "all_debt_eur": 0.0})
            slot["media_eur"] += c["bedrag"]
            slot["periods"].add(c["period"])
            slot["creditors"].append({"crediteur": c["crediteur"], "bedrag": c["bedrag"],
                                      "period": c["period"]})
        elif cat == "unclassified":
            unclassified[c["crediteur"]] = unclassified.get(c["crediteur"], 0.0) + c["bedrag"]

    # the 2025 view names the combined list PRO; GL and PvdA filed separately, so say so
    MERGE = {"GL": "PRO", "PvdA": "PRO"}
    merged: dict[str, dict] = {}
    for name, slot in media_by_party.items():
        key = MERGE.get(name, name)
        dst = merged.setdefault(key, {"partij": key, "media_eur": 0.0, "creditors": [],
                                      "periods": set(), "all_debt_eur": 0.0, "filers": []})
        dst["media_eur"] += slot["media_eur"]
        dst["creditors"] += slot["creditors"]
        dst["periods"] |= slot["periods"]
        dst["filers"].append(name)
    media_by_party = merged

    for slot in media_by_party.values():
        for c in creditors:
            if MERGE.get(c["partij"], c["partij"]) == slot["partij"]:
                slot["all_debt_eur"] += c["bedrag"]
        slot["media_eur"] = round(slot["media_eur"], 2)
        slot["all_debt_eur"] = round(slot["all_debt_eur"], 2)
        slot["media_share_of_debt"] = (round(100 * slot["media_eur"] / slot["all_debt_eur"], 1)
                                       if slot["all_debt_eur"] else None)
        slot["periods"] = sorted(slot["periods"])
        slot["creditors"].sort(key=lambda x: -x["bedrag"])

    rows = sorted(media_by_party.values(), key=lambda r: -r["media_eur"])
    total_media = round(sum(r["media_eur"] for r in rows), 2)
    total_debt = round(sum(c["bedrag"] for c in creditors), 2)

    payload = {
        "meta": {
            "what_this_is": "Debt outstanding to media and advertising suppliers of EUR 25.000 or more, per party.",
            "what_this_is_not": ("Not media spend, and not a floor on media spend. It is the balance still owed "
                                 "to a supplier on the date the party filed: a party that paid on time shows "
                                 "zero, and a party that paid most of a large bill shows only the remainder. "
                                 "A balance says what had not been settled, not what was bought or when. The "
                                 "two periods are disjoint windows ending at different dates and their totals "
                                 "are published separately, never added or subtracted."),
            "source": "BZK gift and debt overviews, Tweede Kamer election 2025 (two ODS files, disjoint periods)",
            "periods": ["2024-01-01..2025-10-08", "2025-10-09..2025-10-29"],
            "creditors_total": len(creditors),
            "creditors_classified": len(creditors) - sum(1 for c in creditors if classify(c["crediteur"]) == "unclassified"),
            "method": "keyword rules, first match wins; unmatched creditors are listed, never reassigned",
        },
        "totals": {
            "media_eur": total_media,
            "all_debt_eur": total_debt,
            "media_share_of_debt": round(100 * total_media / total_debt, 1) if total_debt else None,
        },
        "by_category": {k: round(v, 2) for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1])},
        "media_by_party": rows,
        "unclassified": {k: round(v, 2) for k, v in sorted(unclassified.items(), key=lambda kv: -kv[1])},
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"creditors: {len(creditors)}, classified: {payload['meta']['creditors_classified']}")
    print(f"debt to media suppliers: EUR {total_media:,.2f} of EUR {total_debt:,.2f} "
          f"({payload['totals']['media_share_of_debt']}% of disclosed debt)")
    print("\nby category:")
    for k, v in payload["by_category"].items():
        print(f"  {k:<24}{v:>14,.2f}")
    print("\nper party (media debt):")
    for r in rows:
        print(f"  {r['partij']:<6}{r['media_eur']:>14,.2f}  = {r['media_share_of_debt']:>5.1f}% of its debt"
              f"   {len(r['creditors'])} creditor(s)")
    if unclassified:
        print(f"\nunclassified ({len(unclassified)} names, EUR {sum(unclassified.values()):,.2f}) - left as-is:")
        for k, v in list(payload["unclassified"].items())[:8]:
            print(f"  {k[:52]:<54}{v:>12,.2f}")
    print(f"\nwrote {OUT} ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
