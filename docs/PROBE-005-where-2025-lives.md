# PROBE 005 — why the table stops at 2024, and where 2025 lives

Asked on 2026-11-20, when the dashboard's tables end at 2024 and the query was whether 2025 should be there. It
should, and it is published — just not in the place the dashboard puts it. This is the calendar, from the sources.

## The legal cycle

- **Annual report.** A party with a seat files its financial report for year Y **before 1 July of Y+1**. BZK
  publishes it in **October**. The 2024 reports were published on **22 October 2025** (22-10-2025 on the
  dashboard's `jaarverslagen` rows, which is the publication date, not the report date).
- **Therefore 2025's annual reports** are due **1 July 2026** and are not published. On 2026-11-20 the register's
  newest document is still `jaar: 2024`. That is a publisher lag of the expected length, not a gap in this
  pipeline.
- **Election year adds two disclosures.** For the election of **29 October 2025**, parties filed:
  - gifts and debts for **1 January 2024 to 8 October 2025**, published **22 October 2025**, one week before
    the vote;
  - supplementary overviews for the **final three weeks** (9 to 29 October 2025), submitted by 29 November 2025
    and published by 29 December 2025.
- **The threshold differs by workbook, and they are not interchangeable**: the party gift workbooks state
  €1.000 per donor per year. €767,12 is the **candidate** threshold, in the candidate workbook only. An
  earlier version of this probe applied the €767,12 cutoff to party gifts, which was wrong; the party CSVs
  contain no positive donor total below €1.000.

Sources: rijksoverheid.nl `documenten/2025/10/22/overzichten-financiering-politieke-partijen-2024`,
`actueel/nieuws/2025/10/22/publicatie-overzichten-giften-en-schulden-tweede-kamerverkiezing-2025`, and the BZK
letter of 16 February 2026 replying to the Ctfpp (`open.overheid.nl`, ref. 2026-0000029061).

## Where it actually is

Not on `partijfinanciering.nl`. The dashboard's year pages carry 2022-2024 and its `giften/2025` page returns zero
party cards. The election-year material is published as **ODS spreadsheets** under
`rijksoverheid.nl/site/binaries/site-content/collections/documents/2025/10/22/giften-en-schulden-van-partijen-en-kandidaten-voor-de-tweede-kamerverkiezing-2025/`:

| file | content |
|---|---|
| `overzicht-giften-aan-politieke-partijen-…ods` | gifts to parties and neveninstellingen, 2024 and 2025 columns |
| `overzicht-giften-aan-kandidaten-…ods` | gifts to individual candidates, a layer the annual reports lack |
| `overzicht-schulden-van-politieke-partijen-…ods` | debts of €25.000 or more |

Drop the `/site/` segment from that path and the server answers **200 with an HTML 404 page**. Check the content
type, never the status.

## What the files say

`scripts/ingest_tk2025.py`, `out/gifts-2025-election.csv`, `out/gifts-2025-election.json`:

- **Gifts 2025 to 8 October: €9.148.658,46** across 27 parties.
- Two-year column for parties without a seat in 2024: €9.258.031,72, which equals the sum of the donor rows to the
  cent. **0 of 27 parties fail to reconcile.**
- 3.404 donor rows. GL €2.233.874,32 (670 donors), SP €1.536.307,35 (191), D66 €1.228.601,11 (136),
  PvdA €996.163,09 (311), VVD €729.099,00 (132).

The party numbering does not agree between the summary block and the detail block (`06. BBB` versus `07. BBB`),
and GL and PvdA share the number 02 because they ran on one list. Joining on the label therefore loses BBB
entirely; the join is on the party **name**.

## Candidates

1.168 sheet rows covering **1.166 distinct candidates**. Six rows carry a gift; those rows belong to **four
candidates**, and the four amounts total **€11.499** — €5.000 dated 2023 and €6.499 dated 2025: D66's
P. Bamenga €5.000, CDA's J.M. Zwinkels €2.000, K.P. Klein €3.500, and A.M. der der Spek €999 from Hilte Pass BV.
The €999 is **above** the candidate threshold of €767,12 that the candidate workbook prints, and below the
€1.000 party threshold; it was published because the workbook reports it, not because it cleared the party bar.

Candidate gifts are a smaller object than party gifts and almost unstudied. The file covers 2023, 2024 and 2025
per candidate, so it also back-fills two years the dashboard never had.

## What is still missing, and why

- **2025 annual reports** (income, spending, per-entity split, neveninstellingen): due 1 July 2026, unpublished.
- **The final three weeks of the 2025 campaign**: a separate supplementary overview, published by 29 December 2025.
  Not in the 22 October files, and not ingested here.
- **2026**: nothing. A party reports 2026 in mid-2027.

## One more thing this settled

The Ctfpp's advice on the 2024 accounts records that **BIJ1 filed no financial report at all for 2024**, for the
second year running, and recommends recovering the whole subsidy. The dashboard's `19 of 20` parties for 2024 is
that absence, not a formatting problem here.
