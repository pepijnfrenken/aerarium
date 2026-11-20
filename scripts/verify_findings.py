#!/usr/bin/env python3
"""Assert every figure FINDING-002 and FINDING-003 state. Exits non-zero on any disagreement.

Prose and data drift apart silently. This file is the thing that stops it: if a number in a finding is not
asserted here, it is not verified, and adding one without adding the check is how a repository starts lying.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[1]
fails: list[str] = []


def ck(label: str, got, want, tol: float = 0.6) -> None:
    ok = abs(got - want) <= tol if isinstance(want, (int, float)) and isinstance(got, (int, float)) else got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got!r}")
    if not ok:
        fails.append(f"{label}: got {got!r}, want {want!r}")


d = json.loads((REPO / "out" / "view-data.json").read_text())
typ = json.loads((REPO / "out" / "donor-typology.json").read_text())

# ---- FINDING 002: the register -------------------------------------------------
ck("subsidy 2022", d["subsidy"]["totals"]["2022"], 28873282)
ck("subsidy 2023", d["subsidy"]["totals"]["2023"], 31477637)
ck("subsidy 2024", d["subsidy"]["totals"]["2024"], 29131718)
ck("gifts 2022", d["gifts"]["totals"]["2022"], 6039924.73)
ck("gifts 2023", d["gifts"]["totals"]["2023"], 10064750.01)
ck("gifts 2024", d["gifts"]["totals"]["2024"], 8933589.90)
ck("total gift money", round(sum(d["gifts"]["totals"].values()), 2), 25038264.64)
ck("donors", len(d["gifts"]["donors"]), 2301)
ck("cross-party cases", len(d["gifts"]["cross_party"]), 11)
ck("cross-party total", round(sum(c["total"] for c in d["gifts"]["cross_party"]), 2), 376303.27)

sub = {p["name"]: p["by_year"] for p in d["subsidy"]["parties"]}
gif = {p["name"]: p["by_year"] for p in d["gifts"]["parties"]}
ck("VVD cumulative subsidy", sum(v for v in sub["VVD"].values() if v), 15205620)
ck("VVD cumulative gifts", sum(v for v in gif["VVD"].values() if v), 4349220)
ck("GL cumulative gifts", sum(v for v in gif["GL"].values() if v), 6413923.88, tol=0.05)
ck("SP cumulative gifts", sum(v for v in gif["SP"].values() if v), 6229126.27, tol=0.05)
for name, want in [("GL", 57.0), ("SP", 54.3), ("PvdA", 29.9), ("CDA", 21.9), ("D66", 17.9), ("VVD", 6.6), ("NSC", 2.8)]:
    s, g = sub.get(name, {}).get("2024") or 0, gif.get(name, {}).get("2024") or 0
    ck(f"{name} 2024 gift share", round(100 * g / (s + g), 1), want, tol=0.06)

ent: dict[tuple, float] = {}
for dn in d["gifts"]["donors"]:
    for e in dn["edges"]:
        if e.get("entity"):
            k = (e["jaar"], e["partij"], e["entity"])
            ent[k] = ent.get(k, 0) + e["bedrag"]


def find(year: int, party: str, needle: str) -> float:
    return round(sum(v for k, v in ent.items() if k[0] == year and k[1] == party and needle.lower() in k[2].lower()), 2)


ck("SOV 2023", find(2023, "VVD", "ondersteuning vvd"), 1244932)
ck("Centrum voor Lokaal Bestuur 2024", find(2024, "PvdA", "lokaal bestuur"), 768024.80)
ck("GroenLinks EU 2024", find(2024, "GL", "europese unie"), 212142.16)
ck("CDA Business Club 2024", find(2024, "CDA", "business"), 192948.99)
ck("CU Groen van Prinsterer 2022", find(2022, "CU", "prinsterer"), 122000)
ck("gift entities", len({k[2] for k in ent}), 30)
ck("PVV in subsidy table", "PVV" in sub, False)

ged = {dn["name"]: dn["total"] for dn in d["gifts"]["donors"] if "hees" in dn["name"].lower() and "verhees" not in dn["name"].lower()}
ck("Godefridus variant A", ged.get("Godefridus van Hees Fonds"), 94400)
ck("Godefridus variant B", ged.get("Stichting Godefridus van Heesfonds"), 20000)

# ---- FINDING 002: NFRP --------------------------------------------------------
ck("nfrp entities after KvK join", len({(r["entity"], r["kvk"]) for r in d["nfrp"]}), 11)
ck("nfrp rows in export", len(d["nfrp"]), 24)
ck("nfrp grand total", sum(r["bedrag_k"] for r in d["nfrp"]), 3289)
con = duckdb.connect(str(REPO / "data" / "aerarium.duckdb"), read_only=True)
named = dict(con.execute("""SELECT jaar, sum(bedrag_k) FROM recipient_line
  WHERE lower(regeling) LIKE 'nfrp politieke partijen%' AND NOT anonymised GROUP BY 1""").fetchall())
anon = dict(con.execute("""SELECT jaar, sum(bedrag_k) FROM recipient_line
  WHERE lower(regeling) LIKE 'nfrp politieke partijen%' AND anonymised GROUP BY 1""").fetchall())
rows = dict(con.execute("""SELECT jaar, count(*) FROM recipient_line
  WHERE lower(regeling) LIKE 'nfrp politieke partijen%' GROUP BY 1""").fetchall())
con.close()
ck("nfrp named 2020", named.get(2020), 22)
ck("nfrp named 2023", named.get(2023), 1362)
ck("nfrp named 2024", named.get(2024), 1905)
ck("nfrp anon 2018", anon.get(2018), 462)
ck("nfrp anon 2019", anon.get(2019), 540)
ck("nfrp rows 2021", rows.get(2021, 0), 0)
ck("nfrp rows 2022", rows.get(2022, 0), 0)

# ---- FINDING 002: corpus ------------------------------------------------------
corpus = sorted((REPO / "corpus" / "text").glob("*.txt"))
ck("corpus documents", len(corpus), 92)
split = sum(1 for f in corpus if re.search(r"per entiteit", f.read_text(encoding="utf-8", errors="replace"), re.I))
ck("docs stating a per-entity split", split, 10)
split_recent = sum(1 for f in corpus if f.name[:4] in ("2023", "2024")
                   and re.search(r"per entiteit", f.read_text(encoding="utf-8", errors="replace"), re.I))
ck("of which 2023-2024", split_recent, 10)
named_entity = sum(1 for f in corpus if re.search(r"neveninstelling", f.read_text(encoding="utf-8", errors="replace"), re.I))
ck("docs mentioning neveninstelling", named_entity, 74)

# ---- FINDING 003: who donates -------------------------------------------------
ck("individual donors", typ["counts"]["individual"], 2089)
ck("entity donors", typ["counts"]["entity"], 194)
ck("bequest donors", typ["counts"]["bequest"], 13)
ck("party vehicle donors", typ["counts"]["party_vehicle"], 5)
ck("individual money", typ["money"]["individual"], 18809057)
ck("entity money", typ["money"]["entity"], 4827459)
ck("bequest money", typ["money"]["bequest"], 698798)
ck("vehicle money", typ["money"]["party_vehicle"], 702950)
for p, want in [("GL", 0.3), ("SP", 0.0), ("VVD", 62.1), ("D66", 25.9), ("PvdA", 1.5), ("PvdD", 3.4),
                ("CDA", 29.1), ("Volt", 51.7), ("FvD", 54.1), ("SGP", 72.2), ("BVNL", 79.9),
                ("BBB", 57.4), ("JA21", 62.8), ("DENK", 0.0), ("NSC", 0.0), ("PVV", 30.0)]:
    ck(f"{p} entity share", typ["by_party"][p]["entity_share"], want)
ck("PvdD bequests", typ["by_party"]["PvdD"]["bequest"], 549695)
ck("SP entity money", typ["by_party"]["SP"]["entity"], 1812, tol=0.6)

# GL triangulation: the party's own table vs the register's entity total
pdf_sum = 58553 + 66778 + 83168
ck("GL PDF EU-foundation contributions", pdf_sum, 208499, tol=0)
ck("register GLIEU 2022", find(2022, "GL", "europese unie"), 208499)
meps = ("B. Eickhout", "T. Strik", "K. van Sparrentak")
mep_total = round(sum(e["bedrag"] for dn in d["gifts"]["donors"] if dn["name"] in meps
                      for e in dn["edges"] if e["partij"] == "GL" and e["jaar"] == 2022), 2)
ck("3 MEPs total to GL 2022", mep_total, 238818.66)
ck("3 MEPs direct to party", round(mep_total - pdf_sum, 2), 30319.66)

# VVD's own foundations
def party_edge(party: str, year: int, needle: str) -> float:
    return round(sum(e["bedrag"] for dn in d["gifts"]["donors"] if needle.lower() in dn["name"].lower()
                     for e in dn["edges"] if e["partij"] == party and e["jaar"] == year), 2)


vvd_own = (party_edge("VVD", 2023, "VVD Ondersteuning") + party_edge("VVD", 2023, "Thorbeckefonds")
           + party_edge("VVD", 2023, "Opstelten"))
ck("VVD own foundations 2023", vvd_own, 1810000)
ck("VVD gifts 2023", gif["VVD"]["2023"], 3592775)
ck("Kooien bequest to PvdD", party_edge("PvdD", 2022, "Kooien"), 360000)
ck("Movet Beheer total", round(sum(dn["total"] for dn in d["gifts"]["donors"] if dn["name"] == "Movet Beheer"), 2), 105080)

grows = [r for r in csv.DictReader((REPO / "out" / "gifts_donors.csv").open(encoding="utf-8")) if r["kind"] == "donor-total"]
ck("rows carrying a UBO", sum(1 for r in grows if r["ubo_naam"]), 137)
ck("distinct donor-UBO pairs", len({(r["donor"], r["ubo_naam"]) for r in grows if r["ubo_naam"]}), 134)

print()
if fails:
    print(f"{len(fails)} FAILURE(S):")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("ALL CLAIMS IN FINDINGS 002 AND 003 VERIFIED")
