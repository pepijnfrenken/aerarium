# FINDING 002 — party income, and the donors who appear in more than one place

Dashboard `partijfinanciering.nl` (BZK), donor-level gift pages and subsidy table; Rijksfinancien register
for chapter V. Retrieved 2026-11-20. Amounts in euros unless marked €k. Every party-year was reconciled
before use: the sum of the donor rows equals the party total the same page publishes. **61 party-years, 0
mismatches.** Missing is marked, never estimated.

## Three taps, not one

A parliamentary party draws on at least three published sources in three different registers:

| source | what it publishes | register |
|---|---|---|
| Wfpp subsidy | state money per party per year | dashboard `uitgekeerd` |
| private contributions | private money, per donor per year from €1.000, with the receiving party *or neveninstelling* | dashboard `jaarlijkse verantwoording` |
| NFRP Politieke Partijen | state money to the party's international foundation | register, chapter V |

The gift pages are the richest: per party and year, donor name, place, the amount above €1.000, the entity
that received it, and a payment date. 2.301 distinct donors across 2022-2024.

## Subsidy and gifts, side by side

Cumulative 2022-2024, the window all three years share:

| party | subsidy | gifts | gift share |
|---|---|---|---|
| VVD | 15.205.620 | 4.349.220 | 22,2% |
| GL | 6.267.194 | 6.413.923 | 50,6% |
| SP | 5.755.489 | 6.229.126 | 52,0% |

For 2024 alone the same ratio separates further: GL 57,0%, SP 54,3%, PvdA 29,9%, CDA 21,9%, D66 17,9%,
VVD 6,6%, NSC 2,8%. Two parties take more in private gifts than in state subsidy. That is not a claim about
influence; it is what the two registers say when read together, and neither shows it alone.

Published totals: subsidy 2022 €28.873.282, 2023 €31.477.637, 2024 €29.131.718. Gifts 2022 €6.039.924,73,
2023 €10.064.750,01, 2024 €8.933.589,90.

## Donors in more than one place

**Eleven donor-years, counted under the historical filer definition** — GroenLinks and PvdA filed separately
every year in this window — give to more than one party in the same year, together €376.303,27. Grouping them
retrospectively as PRO removes two GL/PvdA-only cases (€3.991,56 and €3.776,75) and leaves **nine cases and
€368.534,96**. The count is a function of the party definition, so it is named rather than presented as a fact.
The four largest under the historical definition:

| year | donor | total | split |
|---|---|---|---|
| 2023 | Stichting The Dreamery Foundation | 140.000 | D66 100.000; GL 20.000; PvdA 20.000 |
| 2023 | Chipshol 2000 B.V. | 98.400 | BVNL 50.000; FvD 48.400 |
| 2024 | Godefridus van Hees Fonds | 52.200 | VVD 36.200; D66 16.000 |
| 2023 | Piegretia B.V. | 30.000 | FvD 15.000; PVV 15.000 |

Godefridus van Hees Fonds appears in all three years, to D66, VVD, and to two of their neveninstellingen as
well: VVD's JOVD (€7.200 in 2023, again in 2024) and D66's Mr. Hans van Mierlo Stichting (€8.500 in 2024).
The remaining seven are individuals giving between €1.000 and €3.000 to GL, PvdA, Volt, CDA or NSC.

The donor is the join key. It exists only because the Wfpp requires gever and UBO to be named per
contribution. Nothing else in the two registers connects them.

## Gifts do enter the neveninstellingen

The register's subsidy side never names a party's scientific institute. The gift side does, because art. 30
Wfpp obliges the neveninstelling to file its own contributions of €1.000 or more. 30 entities are named as
recipients:

- 2023 VVD, Stichting Ondersteuning VVD Tweede Kamerverkiezing (SOV): €1.244.932
- 2024 PvdA, Centrum voor Lokaal Bestuur: €768.024,80
- 2024 VVD, SOV: €247.795
- 2024 GL, GroenLinks in de Europese Unie: €212.142,16 (2023 €200.683; 2022 €208.499)
- 2024 CDA, Stichting CDA Business Club €192.948,99; Christendemocratische Club voor Fondsenwerving €130.350
- 2022 CU, Mr. G. Groen van Prinsterer-stichting: €122.000

VVD's 2023 gift total is €3.592.775. Two different figures got conflated here in an earlier version. The
register records €1.244.932 received *by* Stichting Ondersteuning VVD Tweede Kamerverkiezing from other donors
in 2023 — money flowing into the foundation, not out of it — and separately records the same foundation giving
€1.300.000 to VVD that year. So one foundation accounts for 34,7% of VVD's reported total, not "mostly" of it,
and the register does not show that the incoming euros are the ones that were passed on.

The wider point stands and is worth separating from the arithmetic: a party-level gift total is not the same
object as what the party's organisations received, and neither is total party income.

**Correction.** Finding 001 concluded from the register alone that neveninstellingen are invisible. That
holds for the *state subsidy* chain only. Private money into them is published, with donor names. The two
statements are about different flows and were collapsed into one in the earlier text.

## Party identity: GroenLinks and PvdA are one party now

Every series in this repository treats GL and PvdA as separate parties, and for 2020-2022 that is correct. It
stops being correct after that. The record:

| date | what happened |
|---|---|
| 2023-07-17 | members of both parties vote for a joint electoral list (91,8% GL, over 87% PvdA) |
| 2023-10-27 | the two Tweede Kamer groups merge into GroenLinks-PvdA |
| 2023-11-22 | first joint election, one list, 25 seats; under Wfpp art. 10 a combined list shares the base amounts pro rata |
| 2025-06 | referendum approves a full merger (88% PvdA, 89% GL) |
| 2026-03-26 | new name announced: Progressief Nederland, PRO |
| 2026-06-10 | the Kamer group is renamed PRO |
| 2026-07-01 | PRO is founded; GroenLinks and PvdA cease to exist as separate parties |

Combined, the bloc that is now PRO is the largest party organisation in this window:

| | subsidy 2022-2024 | gifts 2022-2024 | total |
|---|---|---|---|
| GL + PvdA | 12.755.783 | 7.773.405,02 | **20.529.188** |
| VVD | 15.205.620 | 4.349.220 | 19.554.840 |

So a ranking that puts VVD first and GL third is an artefact of the fusion date. The register is not wrong:
these were two legal parties filing two reports. The chart would be wrong if it left that unsaid, which is why
`out/party-lineage.json` carries the events with sources and dumps them into the page.

## Where a name is not an identity

The same fund appears as `Godefridus van Hees Fonds` (€94.400, 8 contributions) and `Stichting Godefridus van
Heesfonds` (€20.000, one contribution). A lowercased-equality rule counts two donors.

For NFRP recipients there is a real key and it was being ignored. Grouping on the name splits one entity into
three (`Stichting Foundation Max van der Stoel For Democracy…`, `STICHTING FOUNDATION MAX VAN DER STOEL
(FMS)`, `Foundation Max Van Der Stoel (FMS)`), as it does for D66's institute, FICDD, SGP and Animal Politics.
Grouping on the KvK published on the same row collapses 46 register rows and 19 spellings to **11 entities**.
The grand total is unchanged at €3.289k, which is the check that the merge moved labels and not money. Where a
KvK is null (GroenLinks International, Forum for Democracy International) no merge is attempted.

The KvK join is used for NFRP only. The gift pages publish no KvK for the receiving entity, so entity totals
there stay fragmented by spelling, and are reported that way.

## NFRP: a disclosure that switches on and off

Rows naming a recipient, by year, €k:

| 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|
| — | — | 22 | — | — | 1.362 | 1.905 |

Not a gap in the pipeline: the register carries a single **anonymised** row for 2018 (462) and 2019 (540),
six named rows for 2020, **no rows at all for 2021 and 2022**, and then full itemisation for 2023-2024. The
programme names its vintage inside the scheme (`NFRP Politieke Partijen Programma 2022`,
`NFRP Politieke Partijen 2023`), so a row paid in 2023 can belong to the 2022 programme. Summing by payment
year mixes vintages; summing by scheme name is possible and not done here.

## What is absent

- **PVV has no subsidy row** in 2022-2024, while appearing in the gift table with €35.000 (2022), €15.000
  (2023), €0 (2024), each time to `Vrienden van de PVV`. The published tables do not say why. Wfpp art. 8-9
  conditions were read and do not by themselves explain it, so this is recorded as absent, not as zero.
- **The per-entity split of the subsidy** exists in the party PDFs, not in any structured source. The phrase
  `per entiteit` matched the extracted text of **10 of 92** reports, all of them 2023 or 2024 and none in
  2020-2022, so the split is a recent practice rather than an old gap. That is a **text match, not a verified
  reading of each report**: a split stated under other wording is missed, and a passing mention is counted. The
  party-naming pattern matched 74 of 92 texts on the same basis, so the lower count is about the split, not
  about naming.
- **2020 and 2021 annual reports** are linked as `open.overheid.nl/details/ronl-…`, a JavaScript shell that
  returns 607 bytes of HTML to a plain fetch. The document itself is served by the site's attachment endpoint
  (`/overheid/openbaarmakingen/api/v0/attachment/ronl-…`), which needs no key, so all 92 are extractable after
  all. Corrected: earlier text here said 34 of them were not extracted.
- **One document was silently overwritten.** The register carries two distinct 2021 Volt deel-2 documents with
  different `ronl-` ids, and a filename built only from year, party and deel made the second overwrite the
  first. Corpus filenames now carry a hash of the link, so 92 documents produce 92 files.
- **Gifts are published for 2022-2024 only.** 2019-2021 and 2025 render an empty page with €0,00 and zero
  party cards; the store records them as `no-data-published`, never as zero.
- **No licence statement** is printed anywhere on `partijfinanciering.nl`. Publication is required by statute,
  not licensed as open data. Do not describe it as CC-0.
