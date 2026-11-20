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


def load_nfrp_anon() -> list[dict]:
    """NFRP rows where the register publishes an anonymised recipient. They cannot be grouped by KvK, so the
    named table drops them; leaving them out of the page without saying so would overstate how much of that
    money is traceable to a foundation."""
    try:
        import duckdb

        conn = duckdb.connect(str(DB), read_only=True)
        rows = conn.execute(
            """
            SELECT jaar, sum(bedrag_k) AS bedrag_k, count(*) AS rows
            FROM recipient_line
            WHERE lower(regeling) LIKE 'nfrp politieke partijen%'
              AND anonymised
            GROUP BY 1 ORDER BY 1
            """
        ).fetchall()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        return [{"error": f"store unavailable: {exc}"}]
    return [{"jaar": r[0], "bedrag_k": int(r[1] or 0), "rows": r[2]} for r in rows]


def load_typology() -> dict:
    """Aggregate donor typology, from out/donor-typology.json when it exists.

    Only the aggregates go into the page: per-party composition is a table, the 2.301 donor rows are not.
    A class says what a donor is, never why it gave; the register has no field for reason.
    """
    path = REPO / "out" / "donor-typology.json"
    if not path.exists():
        return {}
    t = json.loads(path.read_text(encoding="utf-8"))
    return {
        "counts": t["counts"],
        "money": t["money"],
        "by_party": t["by_party"],
        "classes": t["meta"]["classes"],
        "warning": t["meta"]["warning"],
    }


def load_lineage() -> dict:
    """Party identity across years, plus the combined position of a merged group.

    GroenLinks and PvdA filed separately every year in this dataset, so their rows stay separate. But from
    2023 they campaigned on one list and from 2026-07-01 they are one party (PRO). A ranking that treats them
    as two competitors therefore understates the bloc, so the combined figures are computed here.
    """
    path = REPO / "out" / "party-lineage.json"
    if not path.exists():
        return {}
    lin = json.loads(path.read_text(encoding="utf-8"))
    sub = {p["name"]: p["by_year"] for p in load_subsidy()["parties"]}
    gif = {}
    for r in csv.DictReader(GIFTS.open(encoding="utf-8")):
        if r["kind"] == "donor-total":
            gif.setdefault(r["partij"], {}).setdefault(str(r["jaar"]), 0.0)
            gif[r["partij"]][str(r["jaar"])] += float(r["totaal"] or 0)

    combined = []
    for g in lin.get("groups", []):
        years = sorted({y for m in g["members"] for y in sub.get(m, {})})
        rows = []
        for y in years:
            s_ = sum((sub.get(m, {}).get(y) or 0) for m in g["members"])
            gi = sum((gif.get(m, {}).get(y) or 0) for m in g["members"])
            rows.append({"jaar": int(y), "subsidy": round(s_, 2), "gifts": round(gi, 2),
                         "total": round(s_ + gi, 2)})
        combined.append({
            "name": g["name"], "members": g["members"],
            "single_party_from": g.get("single_party_from"), "note": g.get("note"),
            "by_year": rows,
            "total_subsidy": round(sum(r["subsidy"] for r in rows), 2),
            "total_gifts": round(sum(r["gifts"] for r in rows), 2),
        })
    return {"meta": lin.get("meta", {}), "groups": lin.get("groups", []),
            "events": lin.get("events", []), "renames": lin.get("renames", []),
            "combined": combined}


def load_latest(gifts_totals: dict) -> dict:
    """2025, from the election-year ODS files rather than the dashboard.

    The dashboard stops at 2024. These files do not. BZK published gifts for 1 January 2024 to 8 October 2025 a
    week before the 29 October 2025 vote, and a supplementary set for the final three weeks. Different publisher,
    different format and a lower threshold (EUR 767,12 instead of EUR 1.000), so they are carried in their own
    object and never mixed into the 2022-2024 series.
    """
    out = OUT.parent
    pre = json.loads((out / "gifts-2025-election.json").read_text(encoding="utf-8"))
    debts = json.loads((out / "debts-2025.json").read_text(encoding="utf-8"))
    media_path = out / "media-debt.json"
    media_doc = json.loads(media_path.read_text(encoding="utf-8")) if media_path.exists() else {}

    per: dict[str, dict] = {}
    for row in pre["per_party"]:
        # None, not 0.0: a party absent from the supplementary workbook did not report zero, it filed
        # nothing there. A missing disclosure and a disclosed zero are different facts and the page
        # must be able to tell them apart.
        per[row["partij"]] = {"partij": row["partij"], "gifts_to_8oct": row["totaal_2025"],
                              "donors": row["donors"], "gifts_final_3_weeks": None,
                              "debts_22mo": None, "debts_3wk": None}
    for row in debts["per_party"]:
        slot = per.setdefault(row["partij"], {"partij": row["partij"], "gifts_to_8oct": None, "donors": None,
                                              "gifts_final_3_weeks": None, "debts_22mo": None, "debts_3wk": None})
        slot["gifts_final_3_weeks"] = row["gifts_final_3_weeks"]
        slot["debts_22mo"] = row["debts_2024_to_8oct2025"]
        slot["debts_3wk"] = row["debts_9_to_29oct2025"]

    seats_doc = json.loads((out / "seats.json").read_text(encoding="utf-8"))
    seats_2025 = seats_doc["elections"]["2025"]["seats"]
    # The seats file names the combined list GL-PvdA; the 2025 money tables call it PRO. Seats belong
    # to a LIST, so there is exactly one record for those 20 seats and PRO resolves to it at display
    # time. An earlier version added PRO as a second key holding the same 20 seats, which made the
    # exported map total 170 in a 150-seat chamber. A duplicated alias is not a second allocation.
    SEAT_ALIAS = {"PRO": "GL-PvdA"}
    list_of_filer = {"GL": "PRO", "PvdA": "PRO"}

    # GroenLinks and PvdA filed separately for 2025 but ran one list, and are one party from 2026-07-01. In the
    # 2025 view they are shown as PRO, with the two filers kept visible as evidence. The 2022-2024 map is untouched:
    # there they genuinely were two parties.
    MERGE_2025 = {"GL": "PRO", "PvdA": "PRO"}
    merged: dict[str, dict] = {}
    for r in per.values():
        key = MERGE_2025.get(r["partij"], r["partij"])
        slot = merged.setdefault(key, {"partij": key, "gifts_to_8oct": None, "donors": None,
                                       "gifts_final_3_weeks": None, "debts_22mo": None, "debts_3wk": None,
                                       "filers": []})
        slot["filers"].append(r["partij"])
        for f in ("gifts_to_8oct", "gifts_final_3_weeks", "debts_22mo", "debts_3wk", "donors"):
            v = r.get(f)
            if v is not None:
                slot[f] = (slot[f] or 0) + v
    rows = sorted(merged.values(),
                  key=lambda r: -((r["gifts_to_8oct"] or 0.0) + (r["gifts_final_3_weeks"] or 0.0)))
    to_8oct = round(sum(r["gifts_to_8oct"] or 0.0 for r in rows), 2)
    published = round(pre["totals"]["2025_to_8_oct"], 2)
    if abs(to_8oct - published) > 0.02:
        raise SystemExit(f"latest block does not reconcile: per-party sum {to_8oct:,.2f} against the file's "
                         f"published {published:,.2f} (diff {to_8oct - published:,.2f})")
    last3 = round(sum(r["gifts_final_3_weeks"] or 0.0 for r in rows), 2)
    # Seats belong to a list, money is filed per party. GL and PvdA ran one list, so their money is summed and
    # set against that list's 20 seats. Splitting 20 seats between two filers would be an invented number.
    lists: dict[str, dict] = {}
    for r in rows:
        lst = list_of_filer.get(r["partij"], r["partij"])
        slot = lists.setdefault(lst, {"lijst": lst, "gifts": 0.0,
                                      "seats": seats_2025.get(SEAT_ALIAS.get(lst, lst), 0),
                                      "filers": []})
        slot["gifts"] += (r["gifts_to_8oct"] or 0.0) + (r["gifts_final_3_weeks"] or 0.0)
        slot["filers"].append(r["partij"])
    seat_view = []
    for slot in lists.values():
        slot["gifts"] = round(slot["gifts"], 2)
        slot["per_seat"] = round(slot["gifts"] / slot["seats"], 2) if slot["seats"] else None
        seat_view.append(slot)
    seat_view.sort(key=lambda s: (-(s["per_seat"] or -1)))

    pro_table = next((r for r in rows if r["partij"] == "PRO"), None)
    pro_seats = next((s for s in seat_view if s["lijst"] == "PRO"), None)
    if pro_table and pro_seats:
        want = round((pro_table["gifts_to_8oct"] or 0) + (pro_table["gifts_final_3_weeks"] or 0), 2)
        if abs(want - pro_seats["gifts"]) > 0.02:
            raise SystemExit(f"PRO disagrees between the party table ({want:,.2f}) and the seat table "
                             f"({pro_seats['gifts']:,.2f})")

    return {
        "year": 2025,
        "total_to_8oct": to_8oct,
        "total_final_3_weeks": last3,
        "total_to_election": round(to_8oct + last3, 2),
        "total_2024_full_year": (gifts_totals.get("2024") if "2024" in gifts_totals
                                 else gifts_totals.get(2024)),
        "parties": rows,
        "candidates": pre.get("candidates"),
        "seats_2025": seats_2025,
        "seat_alias": SEAT_ALIAS,
        "seat_view": seat_view,
        "creditors": (debts.get("creditors") or [])[:20],
        "media": media_doc.get("media_by_party") or [],
        "media_totals": media_doc.get("totals") or {},
        "media_unclassified": media_doc.get("unclassified") or {},
        "media_categories": media_doc.get("by_category") or {},
        "creditor_count": debts.get("creditor_count"),
        "debts_22mo_total": round(sum(r["debts_22mo"] or 0.0 for r in rows), 2),
        "debts_3wk_total": round(sum(r["debts_3wk"] or 0.0 for r in rows), 2),
        "note": ("The 2025 column counts gifts received between 1 January and 8 October 2025. Both party workbooks "
                 "state a threshold of EUR 1.000 per donor per year; EUR 767,12 is the CANDIDATE threshold in the "
                 "candidate workbook and does not apply to party gifts. The final-three-weeks column covers 9 to "
                 "29 October 2025. Both columns are periods, not annual-report figures, so neither is comparable "
                 "with the full-year 2022-2024 totals above. Debts are a different flow and are never added to "
                 "gifts. The two debt columns cover disjoint periods (22 months, then 3 weeks) and are not a "
                 "before and an after."),
    }


def main() -> None:
    gifts = load_gifts()
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
                {"id": "tk2025", "label": "BZK — giften en schulden Tweede Kamerverkiezing 2025 (ODS)",
                 "url": ("https://www.rijksoverheid.nl/documenten/2025/10/22/"
                         "giften-en-schulden-van-partijen-en-kandidaten-voor-de-tweede-kamerverkiezing-2025"),
                 "licence": LICENCE_BZK},
                {"id": "tk2025post", "label": "BZK — giften en schulden na de Tweede Kamerverkiezing 2025 (ODS)",
                 "url": ("https://www.rijksoverheid.nl/documenten/2025/12/19/"
                         "giften-en-schulden-van-partijen-en-kandidaten-na-de-tweede-kamerverkiezing-2025"),
                 "licence": LICENCE_BZK},
            ],
            "rules": [
                "A ceiling is not a payment. ceiling_k, realised_k, named_k and anon_k are never summed.",
                "An empty year is not zero. The dashboard has gifts for 2022-2024 only; named/anon is null outside 2017-2024.",
                "Donor names are published as written. No name is merged with another; only runs of whitespace are normalised.",
                "Where named_k plus anon_k differs from realised_k by at most 8k (2017-2023) that is rounding of euro-thousands, not a missing row.",
                "2024 has no anonymised row at all: 29.413k of 33.923k is in no register row. r4 is partial, and says so.",
                "NFRP is the Nederlands Fonds voor Regionale Partnerschappen, the fund that carries the MATRA programme. Its Politieke Partijen window is the one place the state names a party's international foundation as a recipient (chapter V, Buitenlandse Zaken).",
                "Part of the NFRP money is anonymised: 2018 and 2019 are entirely so (1.002k: 462k in 2018 and 540k in 2019), and small anonymised rows appear in later years. Named recipients are therefore a share of NFRP, not all of it.",
                "NFRP rows are named recipients only, and the register carries none for 2021-2022. The scheme name carries the programme vintage, not the payment year.",
                "Gift totals are gross of internal movement: they include transfers from a party's own foundations and salary transfers from its own elected representatives. They do not measure outside influence.",
                "The dashboard's 2025 gift page is empty, but 2025 is published: BZK released ODS overviews for the 29 October 2025 election. An empty page is not an absence of gifts, and 2024 is not the end of the series.",
                "Party spending is not published as a comparable series. 131 campaign-spend lines across 92 reports come in three layouts, and 10 of 31 party-years yield conflicting values for the same year. No spending total is shown; see docs/FINDING-004.",
                "SP's gifts are almost entirely its own elected representatives. Its 2024 report states EUR 1,999,889 received from volksvertegenwoordigers against EUR 2,098,889.33 in gifts: 95.3% is salary surrender, not outside money. Its entity share is 0.0%.",
                "PVV has no row in the subsidy table because it takes nothing through it: its reports for 2021-2024 state subsidies received EUR 0, contributions EUR 150, two members at EUR 75. A missing row here is the party's position, not a gap in the register.",
                "GroenLinks and PvdA are one party now. They filed separately every year here, but campaigned on one list from 2023 and became PRO on 2026-07-01, so their two rows describe one organisation in its last years, not two competitors.",
            ],
        },
        "budget": load_budget(),
        "typology": load_typology(),
        "lineage": load_lineage(),
        "subsidy": load_subsidy(),
        "gifts": gifts,
        "latest": load_latest(gifts["totals"]),
        "nfrp": load_nfrp(),
        "nfrp_anon": load_nfrp_anon(),
        "neven_functie": json.loads((OUT.parent / "neveninstellingen-functie.json")
                                    .read_text(encoding="utf-8"))["entities"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    print(f"  budget years: {len(data['budget'])}")
    print(f"  subsidy parties: {len(data['subsidy']['parties'])}, totals {data['subsidy']['totals']}")
    print(f"  gift years: {data['gifts']['totals']}")
    print(f"  donors: {len(data['gifts']['donors'])}, cross-party cases: {len(data['gifts']['cross_party'])}")
    print(f"  nfrp rows: {len(data['nfrp'])}")
    sp = OUT.parent / "spending-campaign.csv"
    if sp.exists():
        print(f"  campaign-spend lines recorded: {sum(1 for _ in sp.open()) - 1} (no total published, see FINDING-004)")
    lt = data["latest"]
    print(f"  2025 to 8 Oct: {lt['total_to_8oct']:,.2f}; final 3 weeks: {lt['total_final_3_weeks']:,.2f}; "
          f"to election: {lt['total_to_election']:,.2f}")


if __name__ == "__main__":
    main()
