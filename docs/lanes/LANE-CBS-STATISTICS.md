# LANE-CBS-STATISTICS — Do official Dutch statistics measure party/campaign spending?

Research date: 2026-11-20. Method: direct API/page checks (curl + web search/fetch). Read-only; nothing in the repo modified except this file. Nothing is quoted below that was not observed, except where explicitly marked.

## Summary verdict

**No official Dutch statistical series measures political party or campaign spending.** None of the three channels (CBS StatLine, Kiesraad open data, data.overheid.nl) contains a dataset with money amounts for political parties. The only official party-money material is the BZK annual "Overzichten financiering politieke partijen" — yearly PDF documents of *income* (subsidies, gifts above €1,000/donor per year from the 2024 overview (€4,500 in the 2023 vintage), debts above €25,000) filed under the Wet financiering politieke partijen — which is not a statistical series, not machine-readable, and does not report campaign spending. CBS has verkiezingsuitslagen and survey-based participation/trust tables only.

## Findings per source

### 1. CBS StatLine (opendata.cbs.nl)

Checked by querying the CBS OData catalog directly (`https://opendata.cbs.nl/ODataCatalog/Tables`, 5,987 tables total):

- Title contains "politieke" → only 3 hits, none about parties as organisations or money:
  - `71721ned` — Politieke en sociale participatie, 2006 (survey participation)
  - `71723ned` — Politieke kwesties en standpunten; 2006, 2010 en 2012 (survey opinions)
  - `60028` — Politieke participatie: stemvoorkeur en -gedrag, politieke interesse en opinies; 1997–2003, **stopgezet** (verified via ODataCatalog ShortDescription: "Sinds 2003 worden de vragen ... niet langer gesteld")
- Title contains "verkiez" → election result tables only (e.g. `37278` "Verkiezingen; uitslagen Tweede Kamer, 1918-2006", stemgedrag tables 2006–2012). No finances.
- Title contains "giften" → only `70013ned` Mineralenaangiften (MINAS) — unrelated.
- Title contains "leden" → only trade-union membership tables. **There is no CBS "ledentallen politieke partijen" dataset.** Membership numbers for parties are published by the DNPP (Documentatiecentrum Nederlandse Politieke Partijen, Rijksuniversiteit Groningen) — academic, not official statistics.
- Site search on cbs.nl for "politieke partijen" returns trust/participation longreads and unrelated StatLine tables (confidence surveys, patent applicants, PSA workload) — no party-finance table.
- There is no CBS theme page for political parties (cbs.nl `/maatschappij/politieke-partijen` returns 404; theme page is "Overheid en politiek", which contains no party statistics).

**Conclusion: CBS covers political parties only via surveys (participation, trust) — membership share and turnout, no euros.**

### 2. Kiesraad open data

- Holder: Kiesraad organisation page on data.overheid.nl (`https://data.overheid.nl/community/organization/kiesraad`), 38 datasets listed (enumerated via pagination, all four pages scrolled).
- Representative entry: "Databank Verkiezingsuitslagen - Kiesraad", `https://data.overheid.nl/dataset/31924a0b-306c-42a2-a623-98fd9c8e7295`, status Beschikbaar, licence **CC-0 (1.0)**, toegang Publiek.
- All 38 datasets are election results (Verkiezingsuitslag Eerste/Tweede Kamer 2010–2025, Europees Parlement 2009–2024, Gemeenteraad 2014/2018/2022/2026, Provinciale Staten, Waterschappen, Eilandsraad, Kiescollege, herindelingsverkiezingen, referenda). Formats: EML (and CSV for some provincial/waterschap list-level results).
- `data.kiesraad.nl` does not resolve (DNS failure via curl: "Could not resolve host"); the Kiesraad content is hosted as datasets on data.overheid.nl plus the results database at verkiezingsuitslagen.nl.

**Conclusion: 100% votes/results/candidates. Zero money.**

### 3. data.overheid.nl

Found exactly one party-money dataset entry:

- **"Giften en schulden politieke partijen"** — permanent link `https://data.overheid.nl/dataset/1101ed48-ec8b-43a7-ae9b-e3e499f618d5` (slug `giften-en-schulden-politieke-partijen`)
  - Data eigenaar: Ministerie van BZK
  - Status: **"In onderzoek" —** literal page text: "Dit is een dataset in onderzoek. De link naar de data is nog niet beschikbaar. De data-eigenaar is aan het onderzoeken of de data beschikbaar kan komen als open data."
  - Toegang: Beperkt; Licentie: Onbekende licentie; Verwachte publicatiedatum: 31-12-2019 (never published); updated 16-02-2022.
  - Conclusion: no data exists behind this entry. **Not usable.**
- No other dataset on data.overheid.nl carries party spending, campaign expenditure, or party income. (Searched: financiën/financiering/giften/campagne + "politieke partijen"; results were unrelated RVO subsidies, begrotingsstaten, inkoopdata, CBS national-accounts tables.)

### 4. The closest thing that exists (not a dataset): BZK annual overzichten

- Page verified: `https://www.rijksoverheid.nl/documenten/jaarverslagen/2024/10/22/overzichten-financiering-politieke-partijen-2023` ("Jaarverslag, 22-10-2024"). Every parliamentary party must file a financial report and a gifts/debts overview with the minister of BZK each year; the ministry publishes them.
- Contents per the page: (a) giften aan politieke partijen en neveninstellingen, threshold **€4,500 per donor per year in the 2023 vintage**; the 2024 overview states **€1,000** per donor per year, consistent with the Evaluatiewet amendment effective 1 January 2023 (name+address registered); (b) schulden, threshold **€25,000**; (c) financiële verslagen: ontvangen subsidies, giften en overige inkomsten, vermogenspositie, schulden — for 2023 published as two PDF bundels (deel 1: PVV…SP; deel 2: Denk…BVNL).
- Related WOO publication: "Overzicht giften en schulden politieke partijen Tweede Kamerfracties" (2013), indexed at `https://open.overheid.nl/details/ronl-24e71398-96ab-4d8c-9375-e9b86f0f9be1`. [INFERENCE from search snippet; the open.overheid.nl page itself is a JS app and could not be opened for verification.]
- Properties: document series, not a statistical dataset; years 2013→2023 available as annual PDFs (each year its own rijksoverheid.nl page); unit: euros per donor/creditor line items; **no explicit open licence stated on the page**; income-oriented — **campaign/verkiezings spokesperson is not a reporting category**, so campaign spending cannot be derived from it. Since 2026 apparent tightening (gifts ≥€10,000 must be reported to BZK within 3 days per rijksoverheid.nl theme page; new party-finance bill kst-37020-VII in treatment) — direction confirmed by pages found, details not verified.

## Dataset table

| Dataset | ID / URL | Years | Unit | Licence | Covers money? |
|---|---|---|---|---|---|
| CBS StatLine "Politieke participatie" | `60028` (opendata.cbs.nl) | 1997–2003, stopgezet | counts/%, no money | CBS open data (CC-BY 4.0 per StatLine open-data page) | No |
| CBS StatLine "Politieke en sociale participatie, 2006" | `71721ned` | 2006 | survey % | CC-BY 4.0 | No |
| CBS "Vertrouwen verkiezingen, stemprocedure, instellingen, mensen" | `71719ned` | 2006–2012 | survey % | CC-BY 4.0 | No |
| CBS verkiezingsuitslagen (37278, 71277NED, etc.) | opendata.cbs.nl | 1918–2006 (results only) | votes/seats | CC-BY 4.0 | No |
| Kiesraad "Databank Verkiezingsuitslagen" + 37 individual verkiezingsuitslag datasets | `data.overheid.nl/dataset/31924a0b-…` + organisation page | 2009–2026 (per election) | EML/CSV: votes, candidates, zetels | **CC-0 1.0** | No |
| DON "Giften en schulden politieke partijen" (BZK) | `1101ed48-ec8b-43a7-ae9b-e3e499f618d5` | none (never published) | — | unknown | **No data available — restricted, "in onderzoek" since ≤2022** |
| BZK "Overzichten financiering politieke partijen" | rijks\(soverheid\) document pages, e.g. year 2023 dated 22-10-2024 | 2013–2023, one PDF bundle per year | euros, donor/creditor line items | not stated | **Yes, but income only (subsidies, gifts ≥€4,500 in 2023 / ≥€1,000 from 2024, debts ≥€25,000); no campaign spending; PDF only** |

## Verdict on filling the spending gap

Official statistics **cannot** fill the party/campaign spending gap:

1. CBS has no coverage of party finances at all — the variable consistently absent from every catalog search is euros.
2. Kiesraad data is entirely electoral, under ideal CC-0, but measures votes, not money.
3. The BZK overview series is the *only* official money source, and it (a) is incomes, not spending; (b) is annual PDFs with no API or dataset registration; (c) is licence-unstated; (d) thresholds out individual donors below the vintage's cutoff — €4,500 in the 2023 overview, €1,000 in the 2024 one — so the cutoff must be stated per vintage, never as one series-wide number.
4. Any spending analysis must therefore rely on the parties' own filings as re-published by BZK (hand-extracted from PDFs), or party annual reports — neither is an official statistical series.
