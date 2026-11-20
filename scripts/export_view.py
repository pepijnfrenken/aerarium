#!/usr/bin/env python3
"""Build out/view-data.json: everything the showcase page is allowed to draw, with provenance.

Sources, all fetched today:
  budget        out/party-line-disclosure.csv   (rijksfinancien open data, CC-0)
  subsidy       dashboard /dashboard/subsidies  (BZK, per party 2022-2024)
  gifts         dashboard per-party gift pages  (BZK, donor level, 2022-2024)
  nfrp          the Tabularium store            (rijksfinancien register, chapter V)

Every figure carries the id of the source it came from. Nothing is computed here that a source does not
already state, except arithmetic on figures from one and the same source (totals, shares, donor edges).
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GIFTS = REPO / "out" / "gifts_donors.csv"
RECON = REPO / "out" / "gifts_reconcile.csv"
OUT = REPO / "out" / "view-data.json"
DB = REPO / "data" / "aerarium.duckdb"

LICENCE_BZK = ("Geen licentieverklaring op partijfinanciering.nl aangetroffen; publicatie is wettelijk "
               "voorgeschreven (Wfpp art. 21 en 30). Bron: Dashboard partijfinanciering (BZK)")
LICENCE_RF = "CC-0 / publiek domein (Ministerie van Financien)"


def dutch_amount(text: str) -> float | None:
    s = text.strip().replace("€", "").replace("\xa0", "").replace(" ", "")
    if s in ("", "-", "–"):
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def load_budget() -> list[dict]:
    path = REPO / "out" / "party-line-disclosure.csv"
    out = []
    for r in csv.DictReader(path.open(encoding="utf-8")):
        if r["family"] != "politieke-partijen":
            continue
        out.append({
            "jaar": int(r["jaar"]),
            "ceiling_k": int(r["ceiling_k"]) if r["ceiling_k"] else None,
            "realised_k": int(r["realised_k"]) if r["realised_k"] else None,
            # not-published is not zero: the recipient register covers 2017-2024 only, so a year outside it
            # has no named/anonymous split to report. Null, never 0.
            "named_k": None if r["r4"] == "not-published" else int(r["named_k"] or 0),
            "anon_k": None if r["r4"] == "not-published" else int(r["anon_k"] or 0),
            "r4": r["r4"],
            "source": "budget",
        })
    return sorted(out, key=lambda d: d["jaar"])


def load_subsidy() -> dict:
    """Read the published per-party table straight from the page's own figures (no lane dependency)."""
    import urllib.request
    import html as htmlmod
    import re

    url = "https://www.partijfinanciering.nl/dashboard/subsidies"
    req = urllib.request.Request(url, headers={"User-Agent": "aerarium/0.1"})
    page = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")

    def strip(s: str) -> str:
        return htmlmod.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ").strip()

    tables = re.findall(r"(?s)<table.*?</table>", page)
    years: list[int] = []
    totals: dict[int, float] = {}
    parties: list[dict] = []
    for tb in tables:
        cap = re.search(r"(?s)<caption[^>]*>(.*?)</caption>", tb)
        caption = strip(cap.group(1)).lower() if cap else ""
        rows = []
        for tr in re.findall(r"(?s)<tr.*?</tr>", tb):
            cells = [re.sub(r"\s+", " ", strip(c)) for c in re.findall(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
            if cells:
                rows.append(cells)
        if not rows:
            continue
        if "per jaar" in caption and "totaal" in caption:
            yrs = [int(c) for c in rows[0] if re.fullmatch(r"20\d\d", c)]
            years = yrs
            for y, c in zip(yrs, rows[1] if len(rows) > 1 else []):
                v = dutch_amount(c)
                if v is not None:
                    totals[y] = v
        elif "per politieke partij" in caption:
            yrs = [int(c) for c in rows[0] if re.fullmatch(r"20\d\d", c)]
            years = years or yrs
            for r in rows[1:]:
                name = r[0]
                by_year = {}
                for y, c in zip(yrs, r[1:]):
                    by_year[str(y)] = dutch_amount(c)
                parties.append({"name": name, "by_year": by_year})
    return {
        "years": years,
        "totals": {str(k): v for k, v in totals.items()},
        "parties": parties,
        "url": url,
        "licence": LICENCE_BZK,
    }


def load_gifts() -> dict:
    rows = [r for r in csv.DictReader(GIFTS.open(encoding="utf-8")) if r["kind"] == "donor-total"]
    recon = list(csv.DictReader(RECON.open(encoding="utf-8")))

    totals: dict[str, float] = defaultdict(float)
    parties: dict[str, dict] = defaultdict(lambda: {"by_year": defaultdict(float), "donors": defaultdict(set)})
    donors: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "edges": []})
    cross: dict[tuple, dict] = {}

    for r in rows:
        amt = float(r["totaal"] or 0)
        year, party = int(r["jaar"]), r["partij"]
        entity = r["neveninstelling"] or ""
        totals[year] += amt
        parties[party]["by_year"][str(year)] += amt
        if r["donor"]:
            parties[party]["donors"][str(year)].add(r["donor"])
        key = " ".join((r["donor"] or "").split()).lower()
        if key:
            d = donors[key]
            d["name"] = " ".join(r["donor"].split())
            d["total"] += amt
            d["edges"].append({
                "jaar": year, "partij": party, "entity": entity or None,
                "bedrag": round(amt, 2), "datum": r["datum"],
            })
            ck = (year, key)
            cross.setdefault(ck, {"jaar": year, "donor": " ".join(r["donor"].split()), "parties": set(), "total": 0.0})
            cross[ck]["parties"].add(party)
            cross[ck]["total"] += amt

    cross_list = []
    for c in cross.values():
        if len(c["parties"]) > 1:
            cross_list.append({
                "jaar": c["jaar"], "donor": c["donor"],
                "parties": sorted(c["parties"]), "total": round(c["total"], 2),
                "by_party": {},
            })
    for item in cross_list:
        for e in donors[(item["donor"] or "").strip().lower()]["edges"]:
            if e["jaar"] == item["jaar"]:
                item["by_party"][e["partij"]] = round(item["by_party"].get(e["partij"], 0) + e["bedrag"], 2)

    return {
        "totals": {k: round(v, 2) for k, v in sorted(totals.items())},
        "parties": [
            {
                "name": k,
                "by_year": {y: round(v, 2) for y, v in sorted(d["by_year"].items())},
                "donors": {y: len(s) for y, s in sorted(d["donors"].items())},
            }
            for k, d in sorted(parties.items())
        ],
        "donors": [
            {"name": d["name"], "total": round(d["total"], 2), "edges": d["edges"]}
            for _, d in sorted(donors.items(), key=lambda kv: -kv[1]["total"])
        ],
        "cross_party": sorted(cross_list, key=lambda c: -c["total"]),
        "reconciliation": recon,
        "empty_years": [2019, 2020, 2021, 2025],
        "url": "https://www.partijfinanciering.nl/dashboard/jaarlijkse-verantwoording/giften/{jaar}/{slug}",
        "licence": LICENCE_BZK,
    }


def load_nfrp() -> list[dict]:
    """NFRP state money, grouped by KvK.

    The register spells the same recipient several ways ('Foundation Max van der Stoel' / 'STICHTING
    FOUNDATION MAX VAN DER STOEL (FMS)' / 'Foundation Max Van Der Stoel (FMS)'), so grouping on the name
    splits one entity into three. KvK is a legal identifier published on the same row, so it is the key
    used here: rows sharing a KvK are one entity. The variants are kept in the output so the merge can be
    checked rather than believed. Where KvK is null no merge is attempted; the name stands alone.

    Canonical spelling: the one carrying the largest amount in the most recent year that names it.
    """
    try:
        import duckdb

        conn = duckdb.connect(str(DB), read_only=True)
        rows = conn.execute(
            """
            SELECT jaar, ontvanger, kvk, bedrag_k
            FROM recipient_line
            WHERE lower(regeling) LIKE 'nfrp politieke partijen%'
              AND NOT anonymised
            ORDER BY jaar, bedrag_k DESC
            """
        ).fetchall()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        return [{"error": f"store unavailable: {exc}"}]

    groups: dict[str, dict] = {}
    for jaar, ontvanger, kvk, bedrag in rows:
        name = " ".join((ontvanger or "").split())
        key = f"kvk:{kvk}" if kvk else f"name:{name.lower()}"
        g = groups.setdefault(key, {"kvk": kvk or None, "by_year": defaultdict(int),
                                    "variants": defaultdict(lambda: defaultdict(int))})
        g["by_year"][int(jaar)] += int(bedrag or 0)
        g["variants"][name][int(jaar)] += int(bedrag or 0)

    out = []
    for g in groups.values():
        # canonical: biggest amount in the latest year that names this KvK
        latest = max(max(y) for y in g["variants"].values())
        canonical = max(g["variants"].items(),
                        key=lambda kv: (kv[1].get(latest, 0), len(kv[0])))
        for jaar, bedrag in sorted(g["by_year"].items()):
            out.append({
                "jaar": jaar,
                "entity": canonical[0],
                "kvk": g["kvk"],
                "bedrag_k": bedrag,
                "variants": sorted(g["variants"]),
                "rows": sum(1 for v in g["variants"].values() if jaar in v),
            })
    return sorted(out, key=lambda r: (r["jaar"], -r["bedrag_k"]))


def main() -> None:
    data = {
        "meta": {
            "generated_at": "2026-11-20",
            "sources": [
                {"id": "budget", "label": "Rijksbegroting chapter VII, Politieke partijen",
                 "url": "https://www.rijksfinancien.nl/open-data", "licence": LICENCE_RF},
                {"id": "subsidy", "label": "Dashboard partijfinanciering — uitgekeerde subsidies",
                 "url": "https://www.partijfinanciering.nl/dashboard/subsidies", "licence": LICENCE_BZK},
                {"id": "gifts", "label": "Dashboard partijfinanciering — bijdragen van €1.000 of meer",
                 "url": "https://www.partijfinanciering.nl/dashboard/jaarlijkse-verantwoording/giften",
                 "licence": LICENCE_BZK},
                {"id": "nfrp", "label": "Rijksfinancien register — NFRP Politieke Partijen (chapter V)",
                 "url": "https://www.rijksfinancien.nl/open-data", "licence": LICENCE_RF},
            ],
            "rules": [
                "A ceiling is not a payment. ceiling_k, realised_k, named_k and anon_k are never summed.",
                "An empty year is not zero: gifts exist for 2022-2024 only; named/anon is null outside 2017-2024.",
                "Donor names are published as written. No name is merged with another; only runs of whitespace are normalised.",
                "Where named_k plus anon_k differs from realised_k by at most 8k (2017-2023) that is rounding of euro-thousands, not a missing row.",
                "2024 has no anonymised row at all: 29.413k of 33.923k is in no register row. r4 is partial, and says so.",
                "NFRP rows are named recipients only, and the register carries none for 2021-2022. The scheme name carries the programme vintage, not the payment year.",
                "Gift totals are gross of internal movement: they include transfers from a party's own foundations and salary transfers from its own elected representatives. They do not measure outside influence.",
                "The dashboard's 2025 gift page is empty, but BZK published gifts around the 2025 election in a separate overview. An empty page is not an absence of gifts.",
            ],
        },
        "budget": load_budget(),
        "subsidy": load_subsidy(),
        "gifts": load_gifts(),
        "nfrp": load_nfrp(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    print(f"  budget years: {len(data['budget'])}")
    print(f"  subsidy parties: {len(data['subsidy']['parties'])}, totals {data['subsidy']['totals']}")
    print(f"  gift years: {data['gifts']['totals']}")
    print(f"  donors: {len(data['gifts']['donors'])}, cross-party cases: {len(data['gifts']['cross_party'])}")
    print(f"  nfrp rows: {len(data['nfrp'])}")


if __name__ == "__main__":
    main()
