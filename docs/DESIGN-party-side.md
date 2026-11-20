# DESIGN — the party side

Probed 2026-11-20. This widens the project by one publisher (BZK's Dashboard partijfinanciering) and by one
document class (party annual reports as PDF). Stated here because scope widens out loud.

## What the publisher actually is

`partijfinanciering.nl` is a Next.js app: server-rendered HTML for the tables, a Hasura GraphQL API at
`api.partijfinanciering.nl/v1/graphql` for the document index only.

- **GraphQL introspection exposes exactly one table:** `jaarverslagen` (id, partij, jaar, deel, datum, link,
  pages, bestand_grootte_mb). 92 rows: 2020 (14 parties), 2021 (20), 2022 (19), 2023 (20), 2024 (19). `link`
  points at `open.overheid.nl`, i.e. the party's submitted PDF.
- **`/dashboard/subsidies`** is server-rendered and carries the Wfpp subsidy per party per year, 2022-2024.
  Totals as published: 2022 €28.873.282, 2023 €31.477.637, 2024 €29.131.718.
- **`/dashboard/jaarlijkse-verantwoording/giften`** is server-rendered per year, with contributions of
  €1.000+ per party: 2024 total €8.933.589,90 across 20 parties.
- **`/dashboard/over-de-politieke-partijen`** publishes *counts*, not a list: for 2024, 16
  politiek-wetenschappelijke instituten, 12 politieke jongerenorganisaties, 14 neveninstellingen van
  buitenlandse activiteiten, 380.670 subsidiabele leden, 20.476 leden van jongerenorganisaties.
- No route, table or download anywhere on the site carries the list of designated neveninstellingen, and
  `/dashboard/*` has no per-party pages for it. `/dashboard/over-de-politieke-partijen/{partij}` 404s.

## Three numbers for the same money

The same year, the same scheme, three published figures that are three different quantities:

| year | budget JV (realisation) | Rijks register (named + anonymised) | dashboard (uitgekeerd) |
|---|---|---|---|
| 2022 | 27.456k | 27.449k | €28.873.282 |
| 2023 | 29.458k | 29.458k | €31.477.637 |
| 2024 | 33.923k | 4.510k named, 0 anonymised | €29.131.718 |

The register tracks the jaarverslag line closely in 2022-2023 (within 8k) and collapses in 2024. The
dashboard sits above both by €1,4M in 2022 and €2,0M in 2023, and below the 2024 realisation by €4,8M. Nobody
publishes the beschikking that would reconcile them, so the labels do the work they can: `JV` is the
realisation, the register is payments attributed to recipients, and the dashboard is what BZK says it paid.
They are not interchangeable and this repository will not sum them.

## Where the per-entity split lives

Not in any structured source. It is in the PDFs, and the wording differs per party.

**CDA 2024**, cover letter, verbatim: "De totaalbedragen van de uitgegeven subsidie per entiteit zijn:"
Stichting Secretariaat CDA €1.122.033; Stichting Wetenschappelijk Instituut voor het CDA €389.379;
Vereniging Christen Democratisch Jongeren Appèl €133.397; Eduardo Frei Stichting €117.654. Sum €1.762.463
against the dashboard's €2.026.177 for the same party-year. The two labels differ (`uitgegeven` = spent,
`uitgekeerd` = paid), so the €263.714 is not automatically an anomaly: it is two quantities, and the
beschikking that would reconcile them is not published.

**50PLUS 2024**, narrative rather than table, and it states the mechanism: "Het Ministerie van Binnenlandse
Zaken en Koninkrijksrelaties kent in de subsidiebeschikking aan 50PLUS overeenkomstig art. 8 Wfpp ook subsidie
toe aan haar neveninstellingen ... 50PLUS stort deze geoormerkte subsidiegelden één op één door aan deze beide
stichtingen", naming Stichting Wetenschappelijk Instituut 50PLUS and Stichting Jan Nagel 50PLUS Foundation.

So the subsidy for the institutes is legally *theirs*, allocated in the party's beschikking under art. 8, and
the party only passes it through. That is why the Rijks register anonymises at party level and stops: from the
state's side the party is the recipient, and the split downstream is a private bookkeeping act that only the
party reports.

## Why art. 8 matters more than the list

Art. 8 Wfpp publishes the formula, not just a total: a base amount (€275.925) plus a per-seat amount
(€82.883) plus a member component, **plus separate components for each designated neveninstelling type** — a
politiek-wetenschappelijk instituut (base €201.008 + €20.825 per seat), a politieke jongerenorganisatie
(formula over a base, seats and members), and an instelling voor buitenlandse activiteiten (formula over base
and seats), with the amounts updated annually by ministerial regeling (last: Stcrt. 2026, 19658, per 6 June
2026).

That makes the ministry's per-party figures checkable against the statute with seats and member counts as the
only inputs. It also means the neveninstelling layer can be *expected*, not merely observed: a party with a
designated scientific institute is entitled to a computable sum, and a party that receives one without a
designation, or a designation without a payment, is a finding either way.

## Plan, and the bounds of this slice

1. **Adapter `partijfinanciering`**: GraphQL `jaarverslagen` index, the SSR subsidies table, the SSR gifts
   table per year. Provenance per row as everywhere else.
2. **Corpus**: fetch all 92 PDFs, extract text with `pdftotext -layout`, keep text and page offsets. Never
   commit the PDFs; they are re-fetchable from `open.overheid.nl`.
3. **Candidate extraction then adjudication**: a machine pass emits every sentence naming a neveninstelling, a
   wetenschappelijk instituut, a jongerenorganisatie, or a euro amount beside one. The party->entity and
   party->amount edges are then adjudicated by hand into the `adjudication` table with document and page
   evidence, because one regex over five parties' prose would be a guess wearing a number.
4. **Graph**: `party`, `neveninstelling` (category per art. 1(f)), edges `designated_by` and `funded_via`
   carrying the document, the page, the year and the grade.
5. **Art. 8 check** only after 1-4 hold, and only where seats and members are published.

Out of bounds in this slice: municipalities, provinces, waterschappen, EU funds; party spending as opposed to
party income; anything behind a login. No PDF goes into the repo.
