#!/usr/bin/env python3
"""The claim layer: what a donor entity's money is *for*, as opposed to how much it is.

The rule this file enforces, and the reason it exists separately from the money tables:

    A donor entity's philosophy is never inferred. It is either (a) a position the entity
    itself published, quoted with a URL, or (b) the party's own published position on the
    domain in which the entity demonstrably operates. Anything else is `no-claim`.

An external dossier pass over 17 entity donors returned "advocacy positions published by the
entity: none found" for all 17. That is a result, not a gap in the pass, and it is why every
`stated_position` here is null. What remains is the activity the entity does publish (KvK/SBI,
own website) and, against it, what the party it funded says about that domain.

Three classes, and the class is the finding:
  party-vehicle   the party's own support foundation. Its agenda is the party's; it is not
                  outside money and must never be counted as evidence of external influence.
  sector-mapped   a trading or operating company. The domain is documented; the *direction*
                  of its interest is not. "A dairy trader funds BBB" is compatible with
                  influence and equally compatible with nothing.
  no-claim        a holding with no published activity. Nothing can be said, and nothing is.
"""

import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "out" / "gifts_donors_public.csv"
OUT = ROOT / "out" / "donor-claims.json"

# Entity -> claim record. `match` is the substring used against the register's donor strings.
# Activity, SBI and leadership all come from docs/lanes/LANE-ENTITY-DOSSIERS.md, which cites a URL per fact.
ENTITIES = [
    {
        "name": "Stichting Ondersteuning VVD Tweede Kamerverkiezing",
        "match": "ondersteuning vvd",
        "claim": "party-vehicle",
        "activity": "VVD campaign-support foundation (ondersteuningsstichting)",
        "subject": None,
        "stated_position": None,
        "basis": "Follow the Money party-financing investigation identifies it as one of the VVD's support foundations and reports ~EUR 1.2m to the party in the analysed period.",
        "source": "https://www.ftm.nl/artikelen/partijfinanciering",
        "caveat": "Not outside money. Counting this as third-party influence would double-count the party's own campaign financing.",
    },
    {
        "name": "Stichting Het Thorbeckefonds",
        "match": "thorbeckefonds",
        "claim": "party-vehicle",
        "activity": "VVD fundraising foundation, named after Thorbecke, publishes annual accounts",
        "subject": None,
        "stated_position": None,
        "basis": "Media reporting describes it as funding VVD campaigns partly from investment returns.",
        "source": "https://www.nporadio1.nl/nieuws/politiek/f02b101f-aa34-4b08-9ff8-49d6328e00a0/vvd-financiert-campagne-mede-uit-beurswinst",
        "caveat": "Not outside money; a party fundraising vehicle.",
    },
    {
        "name": "Stichting Ivo Opstelten Foundation",
        # The alias must identify the entity AS THE DONOR. A looser 'opstelten' matched
        # 'I. Opstelten', a person whose €1,000 went INTO the foundation - the foundation is the
        # recipient on that row, not the donor. That single false edge moved a published
        # subtotal by EUR 1,000 and put a private individual in an entity total.
        "match": "ivo opstelten foundation",
        "claim": "party-vehicle",
        "activity": "VVD-linked support foundation (KvK 27342104), ANBI, has its own VVD-hosted page",
        "subject": None,
        "stated_position": None,
        "basis": "Own annual report and ANBI filing published via vvd.nl.",
        "source": "https://www.vvd.nl/ivo-opstelten-foundation/",
        "caveat": "Not outside money. NRC reported in 2017 that the VVD broke tax law with the foundation; no enforcement decision was found.",
    },
    {
        "name": "Chipshol 2000 B.V.",
        "match": "chipshol",
        "claim": "sector-mapped",
        "activity": "Land development around Schiphol; ~100 lawsuits against the state, Schiphol and LVNL since 1993",
        "subject": "luchtvaart en ruimtelijke ordening rond Schiphol",
        "stated_position": None,
        "basis": "The entity's litigation IS its published position: it claims the state and Schiphol unlawfully blocked its development. Gerechtshof Arnhem-Leeuwarden, 25 March 2025, held the Rechtbank Den Haag acted unlawfully and partially 1994-1998. Claims reported at up to EUR 6bn.",
        "source": "https://www.accountant.nl/nieuws/2025/3/chipshol-wil-compensatie-van-staat-na-uitspraak-gerechtshof/",
        "caveat": "A litigation position is a documented interest, not a policy programme. No published statement on party policy was found.",
    },
    {
        "name": "Trigona Dairy Trade B.V.",
        "match": "trigona",
        "claim": "sector-mapped",
        "activity": "Dairy and non-dairy commodity trading for industry, foodservice and retail (KvK 30130720)",
        "subject": "zuivel en landbouwmarktordening",
        "stated_position": None,
        "basis": "Company's own about page: dairy commodity trading, GMP-FSA, SKAL (BIO) and BRC certified.",
        "source": "https://www.trigonadairytrade.nl/about",
        "caveat": "Operating in the funded party's core policy domain. The direction of interest - more or less regulation, more or less nitrogen space - is not published and is not inferred.",
    },
    {
        "name": "Graansloot Kampen B.V.",
        "match": "graansloot",
        "claim": "sector-mapped",
        "activity": "Inland terminal: transshipment, storage and processing of grain, oilseeds and feedstocks",
        "subject": "agrologistiek en grondstoffen",
        "stated_position": None,
        "basis": "Company's own pages: dry bulk transshipment and storage, GMP+ FSA, EU Organic, AEO certified.",
        "source": "https://www.graansloot.nl/over-graansloot-kampen",
        "caveat": "Same limit as Trigona: the domain is documented, the direction is not.",
    },
    {
        "name": "Lambda Furtherance B.V.",
        "match": "lambda furtherance",
        "claim": "sector-mapped",
        "activity": "Wholesale of other building materials (KvK 27265414); supplies PANACEA polyacrylonitrile fibre",
        "subject": "bouw en bouwmaterialen",
        "stated_position": None,
        "basis": "SBI registration plus the company's own product site.",
        "source": "https://lambdaphi.nl/",
        "caveat": "Sector from SBI and product line only. No position published.",
    },
    {
        "name": "Sensemakers BV",
        "match": "sensemakers",
        "claim": "sector-mapped",
        "activity": "ICT / internet services / web portals; operates AS47121",
        "subject": "internet en digitale infrastructuur",
        "stated_position": None,
        "basis": "SBI web portals and a public ASN allocation.",
        "source": "https://internetdata.io/AS47121",
        "caveat": "No informative website content retrieved; sector is from SBI and the ASN record.",
    },
    {
        "name": "Ozephius Group B.V.",
        "match": "ozephius",
        "claim": "sector-mapped",
        "activity": "Holding company (KvK 24213791); related entity Ozephius Stainless B.V., metal processing",
        "subject": "metaal en industrie",
        "stated_position": None,
        "basis": "Registry entries for the holding and for Ozephius Stainless B.V.",
        "source": "https://companyinfo.nl/organisatieprofiel/metaalbewerking/ozephius-stainless-b-v-oud-beijerland-24275586-000016148134",
        "caveat": "The holding itself does nothing public; the sector is inferred from a related entity, which is a weaker basis than a direct SBI code.",
    },
    {
        "name": "Sjopperdepop BV",
        "match": "sjopperdepop",
        "claim": "sector-mapped",
        "activity": "Wholesale of household, office and shop furniture (Haarlem)",
        "subject": "retail en meubelgroothandel",
        "stated_position": None,
        "basis": "SBI registration.",
        "source": "https://companyinfo.nl/organisatieprofiel/groothandel-in-huishoudelijke-kantoor-en-winkelmeubelen/sjopperdepop-b-v-haarlem-34173293-000019650140",
        "caveat": "Sector from SBI only. The company's own about page could not be read.",
    },
    {
        "name": "Stichting Dona",
        "match": "stichting dona",
        "claim": "sector-mapped",
        "activity": "Duurzame Ontwikkeling Nederland Afrika (KvK 41158157), ANBI development foundation",
        "subject": "ontwikkelingssamenwerking",
        "stated_position": None,
        "basis": "The foundation's own objectives page and ANBI page.",
        "source": "https://stichtingdona.nl/over-dona/",
        "caveat": "A development foundation funding a party that wants lower development spending is a tension worth quoting both sides of, not resolving here.",
    },
    {
        "name": "Stichting The Dreamery Foundation",
        "match": "dreamery",
        "claim": "no-claim",
        "activity": "Foundation; publishes multi-year policy plans (2023-2025, 2026-2028)",
        "subject": None,
        "stated_position": None,
        "basis": "Policy plans published at dreamery.org; the substantive mission was not extracted.",
        "source": "https://dreamery.org/",
        "caveat": "It publishes policy plans, so a position probably EXISTS - it simply has not been read. This is the one entity where reading the document would move it out of no-claim.",
    },
    {
        "name": "Mega Management B.V.",
        "match": "mega management",
        "claim": "no-claim",
        "activity": "Financial holding (KvK 33164658); bankruptcy declared 2026",
        "subject": None,
        "stated_position": None,
        "basis": "SBI financial holdings. Insolvency 2026, rechtbank Limburg F.03/26/254.",
        "source": "https://failliet.org/zaken/03.lim.26.254.F.1329.1.26",
        "caveat": "No published activity, so no domain and no claim. Note the donation predates the insolvency.",
    },
    {
        "name": "Ka Ve Invest B.V.",
        "match": "ka ve invest",
        "claim": "no-claim",
        "activity": "Financial holding, Schiphol (KvK 28092930)",
        "subject": None,
        "stated_position": None,
        "basis": "SBI financial holdings; no underlying activity published.",
        "source": "https://www.transfirm.nl/nl/organisatie/28092930-000004964810-ka-ve-invest-b.v.",
        "caveat": "A holding at a Schiphol address is not evidence of a Schiphol interest. No claim drawn.",
    },
    {
        "name": "Keurvorst B.V.",
        "match": "keurvorst",
        "claim": "no-claim",
        "activity": "Group parent / holding (KvK 58639209)",
        "subject": None,
        "stated_position": None,
        "basis": "SBI holdings (non-financial); subsidiary activity not established.",
        "source": "https://companyinfo.nl/organisatieprofiel/overige-activiteiten-van-hoofdkantoren/keurvorst-b-v-utrecht-58639209-000027977331",
        "caveat": "Subsidiaries unestablished, so the money's domain is unknown.",
    },
    {
        "name": "Movet Beheer B.V.",
        "match": "movet",
        "claim": "no-claim",
        "activity": "Holding / management entity, Loenen aan de Vecht (KvK 33299469)",
        "subject": None,
        "stated_position": None,
        "basis": "Registry only. Several same-named B.V.s exist, so even the KvK match is unconfirmed.",
        "source": "https://www.creditsafe.com/business-index/nl-nl/company/movet-beheer-bv-nl02001116",
        "caveat": "Identity caveat: the donor entity's KvK cannot be confirmed from free sources.",
    },
    {
        "name": "Op de Mast B.V.",
        "match": "op de mast",
        "claim": "no-claim",
        "activity": "Nothing found (KvK 87542625, Leiderdorp)",
        "subject": None,
        "stated_position": None,
        "basis": "No SBI description, website or business description retrievable.",
        "source": "https://www.compadex.com/nl/businesses/nl/op-de-mast-b-v-87542625-53451767",
        "caveat": "Nothing found is not nothing exists. Recorded as unknown.",
    },
]


def main() -> int:
    totals: dict[str, dict[str, float]] = {}
    by_year: dict[str, dict[str, float]] = {}
    # Rows where the entity appears as the RECIPIENT (neveninstelling) and an individual is the
    # donor are inflows INTO the entity, not gifts from it to the party. They are a separate edge
    # and must never be added to the entity's giving.
    inflow: dict[str, dict[str, float]] = {}
    with SRC.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["kind"] != "donor-total":
                continue
            low = r["donor"].lower().strip()
            recip = (r.get("neveninstelling") or "").lower().strip()
            for e in ENTITIES:
                if e["match"] in low:
                    amt = float(r["totaal"] or 0)
                    totals.setdefault(e["name"], {}).setdefault(r["partij"], 0.0)
                    totals[e["name"]][r["partij"]] += amt
                    by_year.setdefault(e["name"], {}).setdefault(str(r["jaar"]), 0.0)
                    by_year[e["name"]][str(r["jaar"])] += amt
                elif e["match"] in recip:
                    amt = float(r["totaal"] or 0)
                    inflow.setdefault(e["name"], {}).setdefault(str(r["jaar"]), 0.0)
                    inflow[e["name"]][str(r["jaar"])] += amt

    out_entities = []
    for e in ENTITIES:
        parties = {p: round(v, 2) for p, v in sorted(totals.get(e["name"], {}).items(), key=lambda kv: -kv[1])}
        out_entities.append({
            "name": e["name"],
            "claim_type": e["claim"],
            "activity": e["activity"],
            "subject": e["subject"],
            "stated_position": e["stated_position"],
            "basis": e["basis"],
            "source": e["source"],
            "caveat": e["caveat"],
            "total_eur": round(sum(parties.values()), 2),
            "by_party": parties,
            "by_year": {k: round(v, 2) for k, v in sorted(by_year.get(e["name"], {}).items())},
            "received_from_others_eur": round(sum(inflow.get(e["name"], {}).values()), 2),
            "received_by_year_eur": {k: round(v, 2) for k, v in sorted(inflow.get(e["name"], {}).items())},
        })

    out_entities.sort(key=lambda d: -d["total_eur"])
    classes: dict[str, dict] = {}
    for d in out_entities:
        c = classes.setdefault(d["claim_type"], {"entities": 0, "total_eur": 0.0, "parties": {}})
        c["entities"] += 1
        c["total_eur"] = round(c["total_eur"] + d["total_eur"], 2)
        for p, v in d["by_party"].items():
            c["parties"][p] = round(c["parties"].get(p, 0.0) + v, 2)

    grand = round(sum(d["total_eur"] for d in out_entities), 2)
    payload = {
        "generated_by": "scripts/donor_claims.py",
        "source": {
            "money": "out/gifts_donors_public.csv (dashboard donor totals, 2022-2024)",
            "entity_facts": "docs/lanes/LANE-ENTITY-DOSSIERS.md (a URL per fact)",
            "unit": "EUR to the cent",
        },
        "question": "Do the donor entities push an agenda, and can a philosophy be sourced for them?",
        "headline": (
            f"For {len(out_entities)} selected donor entities, no published political or philosophical position "
            f"was found in the material that was read. That is 0 of {len(out_entities)}, and it is a statement "
            f"about these entities and this reading, not about donor entities in general: they were selected by "
            f"size of giving rather than sampled, and a policy plan that was never retrieved can hold what was "
            f"not found."
        ),
        "negative_scope": (
            "This is not a population-level finding about donor entities. It covers the listed entities only, "
            "and only what was retrieved and read for each. Silence in this file is not evidence of silence "
            "by the entity."
        ),
        "rule": "A position is quoted from the entity's own publication, or it is null. Activity is from KvK/SBI or the entity's own site. No motive is inferred from a gift.",
        "classes": classes,
        "grand_total_eur": grand,
        "entities": out_entities,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False))

    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  {payload['headline']}")
    print(f"\n  {'class':<16}{'entities':>9}{'EUR':>14}")
    for c, agg in sorted(classes.items(), key=lambda kv: -kv[1]["total_eur"]):
        print(f"  {c:<16}{agg['entities']:>9}{agg['total_eur']:>14,.2f}  ({100*agg['total_eur']/grand:.1f}%)")
    print(f"  {'TOTAL':<16}{len(out_entities):>9}{grand:>14,.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
