#!/usr/bin/env python3
"""Classify every donor in the register and write out/donor-typology.json.

Four classes, and the rule that assigns each one. This is a *name and register* classification: it says what
kind of thing a donor is, never why it gave. Motive is not in the register and is not inferred here.

  party_vehicle  the donor is a vehicle of the party that received the money. Assigned only on evidence:
                 the register itself tags the name as a neveninstelling of that same party, or the party's own
                 annual report lists it (recorded in PARTY_VEHICLE_DOCUMENTED with the source).
  bequest        the register names an estate or a notary acting for one ('nalatenschap', 'erven', 'p/a ...
                 notaris'). Money from a dead person cannot be explained by that person's current interest.
  entity         a company, holding, foundation or fund: the name carries a legal form or an organisational
                 noun. This is the class where commercial interest is plausible, not proven.
  individual     everything else: a natural person's name.

Known error modes, stated rather than hidden: a person whose surname is also an organisational noun is
misclassified as entity ('G. Groep-Eijsackers' -> entity); a company whose name carries no legal form is
misclassified as individual. The classes are a description of the population, not a claim about any one row.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "out" / "view-data.json"
OUT = REPO / "out" / "donor-typology.json"

LEGAL = re.compile(
    r"\b(b\.?v\.?|n\.?v\.?|v\.?o\.?f\.?|holding|beheer|stichting|fond|foundation|group|groep|invest|capital|"
    r"participaties|vastgoed|management|adviesbureau|vereniging|club|maatschap|coöperatie|cooperatie|"
    r"trust|inc|ltd|gmbh|b\.v\.i\.o\.?)\b",
    re.I,
)
BEQUEST = re.compile(r"(nalatenschap|\berven\b|\berfgenaam\b|p/a\s+\S+\s*notaris|notariskantoor|notarissen)", re.I)
PERSON = re.compile(r"^[A-Z]\.?\s?[A-Z]?\.?\s?[A-Za-z\u00c0-\u017f\-\' ]{2,40}$")

# Vehicles the register never tags as recipients but the party's own report names as its neveninstelling.
# Source per entry, because an entry without a source is a guess.
PARTY_VEHICLE_DOCUMENTED = {
    # VVD 2024 annual report, "Actueel overzicht van de neveninstellingen": Stichting Ivo Opstelten
    # Foundation; Stichting Ondersteuning VVD Tweede Kamerverkiezing; Stichting het Thorbeckefonds.
    "stichtinghetthorbeckefonds": ("VVD", "VVD jaarverslag 2024, overzicht neveninstellingen"),
    "stichtingthorbeckefonds": ("VVD", "VVD jaarverslag 2024, overzicht neveninstellingen"),
    "stichtingthorbeckefondsen": ("VVD", "VVD jaarverslag 2024, overzicht neveninstellingen"),
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main() -> int:
    d = json.loads(DATA.read_text(encoding="utf-8"))

    tagged = defaultdict(set)
    for dn in d["gifts"]["donors"]:
        for e in dn["edges"]:
            if e.get("entity"):
                tagged[e["partij"]].add(norm(e["entity"]))

    donors = []
    for dn in d["gifts"]["donors"]:
        name = dn["name"]
        n = norm(name)
        parties = sorted({e["partij"] for e in dn["edges"]})
        kind, basis = None, None

        for p in parties:
            if n in tagged.get(p, set()) and n not in PARTY_VEHICLE_DOCUMENTED:
                kind, basis = "party_vehicle", f"register tags this name as {p} neveninstelling"
                break
        if kind is None and n in PARTY_VEHICLE_DOCUMENTED and PARTY_VEHICLE_DOCUMENTED[n][0] in parties:
            kind, basis = "party_vehicle", PARTY_VEHICLE_DOCUMENTED[n][1]
        if kind is None and BEQUEST.search(name):
            kind, basis = "bequest", "name carries nalatenschap/erven/notaris"
        if kind is None and LEGAL.search(name):
            kind, basis = "entity", "name carries a legal form or organisational noun"
        if kind is None:
            kind, basis = "individual", "no legal form; person-shaped name"

        donors.append({
            "name": name,
            "kind": kind,
            "kind_basis": basis,
            "total": dn["total"],
            "parties": parties,
            "years": sorted({e["jaar"] for e in dn["edges"]}),
            "edges": len(dn["edges"]),
            "via_entity": sorted({e["entity"] for e in dn["edges"] if e.get("entity")}),
        })

    comp: dict[str, Counter] = defaultdict(Counter)
    for dn in donors:
        for e_ in [dn]:
            for _ in range(dn["edges"]):
                pass
    # money composition per party, recomputed from edges so multi-party donors split correctly
    for dn in d["gifts"]["donors"]:
        k = next(x["kind"] for x in donors if x["name"] == dn["name"])
        for e in dn["edges"]:
            comp[e["partij"]][k] += e["bedrag"]

    by_party = {}
    for p, c in comp.items():
        tot = sum(c.values())
        by_party[p] = {
            "total": round(tot, 2),
            **{k: round(v, 2) for k, v in c.items()},
            "entity_share": round(100 * c["entity"] / tot, 1) if tot else None,
        }

    kinds = Counter()
    money = Counter()
    for dn in donors:
        kinds[dn["kind"]] += 1
        money[dn["kind"]] += dn["total"]

    out = {
        "meta": {
            "generated_from": "out/view-data.json",
            "donors": len(donors),
            "classes": ["party_vehicle", "bequest", "entity", "individual"],
            "warning": (
                "A class describes what a donor is, never why it gave. The register has no field for reason, "
                "purpose or interest. Any statement about motive must be sourced to the donor or to reporting."
            ),
            "known_false_positives": [
                "G. Groep-Eijsackers: a person, classified entity because 'groep' is in the surname.",
            ],
        },
        "counts": dict(kinds),
        "money": {k: round(v, 2) for k, v in money.items()},
        "by_party": dict(sorted(by_party.items(), key=lambda kv: -kv[1]["total"])),
        "donors": sorted(donors, key=lambda x: -x["total"]),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    print("counts:", dict(kinds))
    print("money :", {k: f"{v:,.0f}" for k, v in money.items()})
    print(f"\n{'party':<8}{'total':>13}{'individual':>13}{'entity':>13}{'bequest':>12}{'vehicle':>12}  entity%")
    for p, v in out["by_party"].items():
        print(f"{p:<8}{v['total']:>13,.0f}{v.get('individual',0):>13,.0f}{v.get('entity',0):>13,.0f}"
              f"{v.get('bequest',0):>12,.0f}{v.get('party_vehicle',0):>12,.0f}   {v['entity_share']:5.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
