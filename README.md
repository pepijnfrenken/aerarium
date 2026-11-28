# AERARIUM

Two ledgers the Dutch state publishes separately: what political parties and their neveninstellingen receive, and
what the state pays out. There is no shared identifier between them. This repository builds the join, and grades
every euro by how far along the chain it can still be followed.

**[Read the ledger →](https://pepijnfrenken.github.io/aerarium/)**

## What it does

The register tells you a party got money. It does not tell you who gave it, what an entity is for, or whether the
money arrived before an election. AERARIUM joins five published sources:

| source | what it gives |
|---|---|
| Rijksfinancien open data (CC-0) | the party line in chapter VII, ceiling and realisation, per year |
| Rijksfinancien register | named recipients, chapter V NFRP foundations with KvK |
| Dashboard partijfinanciering (BZK) | subsidy paid per party; every contribution of €1.000+ that a party disclosed, with the donor name — and a date only where the party gave one, which is €8,93m of the €25,04m in the register |
| the parties' own Wfpp reports | the per-entity split, the neveninstellingen list, the spending |
| Algemene Rekenkamer publications | audit findings, attached by document classification because no key exists |

Every figure carries its source, its vintage and the document that holds it. Where a chain breaks, the break is
the finding.

## Headline results

- **2024 is not where the data ends.** 2025 is published by a different route: BZK released ODS overviews for the
  29 October 2025 election. **€10.169.959,32** in gifts was recorded for parties in 2025 up to election day,
  against €8.933.589,90 in all of 2024. Of that, **€1.021.300,86** arrived in the final three weeks.

- **2.301 donors, €25.038.264,64** in contributions 2022-2024, every party-year reconciled to the euro before use.
- **Gift money is 75% individuals, 19% entities, 3% bequests, 3% party vehicles.** Entity share ranges from 0,0%
  (SP) and 0,3% (GL) to 79,9% (BVNL) and 72,2% (SGP): two different systems, not a gradient.
- **The largest "donors" are the parties.** VVD's biggest is VVD: €1.810.000 of its €3.592.775 in 2023 came from its
  own foundations. SP's and GL's biggest are their own elected representatives under a salary-transfer rule.
- **GroenLinks and PvdA are one party now (PRO).** Read together they are the largest organisation in the window:
  €20.529.188 against VVD's €19.554.840.
- **Donations cluster in campaign windows — among donors whose gifts carry a date.** €1.135.143 arrived in the
  90 days before the 22 November 2023 election: 36,5% of all dated 2023 contributions, 1,75× the same calendar
  window a year earlier. The concentration is uneven and it moves with how much of a party's money is dated at
  all. CDA: 95,4% of its *dated* 2023 gifts, but those dated gifts are only 27,5% of its 2023 total, so 26,3% of
  everything it received. SP: 28,3% of its dated gifts (71,5% dated), 20,2% of everything. SP's pattern is
  consistent with salary transfers rather than campaigns; the register records no purpose field, so that
  remains an interpretation, not a finding.
- **The state side stops at the party.** 2024: 20 parties named, €4.510k attributed, €29.413k in no register row at
  all. Only 10 of 92 annual reports state the per-entity split.
- **NFRP**: a single anonymised row for 2018 and 2019, nothing at all for 2021-2022, then named rows for
  2023-2024 — named, not necessarily complete: 46 rows in 19 spellings collapse to 11 entities by KvK.
- **Gifts to candidates are almost unstudied.** The 2025 workbook lists 1.166 distinct candidates. **Six rows
  carry an amount, representing four people across 2023-2025**, and the workbook's combined total is €11.499.
  Only **€6.499 of that falls in 2025**, to three candidates — Klein €3.500, Zwinkels €2.000, and one at €999,
  above the €767,12 candidate threshold. The largest single amount is €5.000 to D66's P. Bamenga, dated
  21 October 2023, not 2025.
- **€177.167,9m of recipient money has no appropriation line behind it.** Two instrument types carry it:
  `Bekostiging` (chapter XVI appropriates €435.738k in 2024 while the register records €24.419.057k across 30
  recipients) and `Bijdrage aan sociale fondsen` (a €20.000k line against €13,9–23,2bn a year in 2018–2021).
  These are premium- and fund-financed flows, not appropriated money, and they carry their own grade:
  *recorded at the recipient, financed outside the appropriation*.
- **The join covers 46% of expenditure, and that is the honest ceiling.** Only **€3.381,0bn of €7.392,5bn** of
  expenditure carries an instrument label the recipient register also uses; **€4.000,6bn (54,1%)** is labelled with
  policy instrument names the register never prints, so no recipient row can sit under it — a naming difference, not
  a failure to disclose. The `rbv_model` column, which looks like the bridge between the two vocabularies, is blank
  in all 44.352 expenditure rows. Of the 42 overshoot groups, 13 are financed outside the appropriation, 16 sit in
  chapters that route money through another chapter, and **13 (€4.744,9m) remain genuinely unexplained**.
- **Rung 6 has a corpus, not a claim.** The Rekenkamer publishes no data feed, so the register was enumerated from
  its own sitemap and harvested whole: **2.677 of 2.677 publications** (2016–2026). **1.003** name a ministry in
  their own title, **482** of those are audit findings. No PDF text has been read, so no euro is graded at rung 6.

## Layout

    out/index.html               the ledger page: markup + two embedded payloads, no network, renders from file://
    out/assets/app.js            the page's application script (editable source)
    out/assets/styles.css        the page's stylesheet (editable source)
    out/view-data.json           the party side, as the page draws it, with source ids
    out/state-data.json          the state side, as the page draws it (spending, join coverage, rung 6)
    out/gifts_donors_public.csv  donor rows, no addresses
    out/neveninstellingen.csv    242 rows: entities named by each party in its own report
    out/donor-typology.json      2.301 donors in four classes
    out/party-lineage.json       when a name stopped meaning the same party
    out/gift-timing.json         donations by date, against election days
    out/flow.json                reachability and the claim join, split by financing basis
    out/govrun.json              expenditure by chapter, the `vuo` axis, instrument classes
    out/thinktanks.json          what the state pays policy institutes and party foundations
    out/media-debt.json          balances owed to media at filing (a balance, never spend)
    out/donor-claims.json        the scoped negative: no position found in the material read
    out/rekenkamer.json          the publication register, classified by title and document kind
    out/overshoots.json          every chapter x instrument overshoot, with its class and the numbers behind it
    out/gifts-2025-election.json 2025 gifts to 8 Oct, per party, from the election-year ODS
    out/gifts-2025-post-election.csv  the final three weeks, 9-29 Oct 2025
    out/candidate-gifts-2025.csv  1.168 sheet rows = 1.166 distinct candidates; 6 rows carry a gift
    out/debts-2025.json          debts, in two disjoint periods that are never subtracted
    docs/INDEX.md                what each document is, and which are load-bearing
    docs/                        contracts, findings, probes, audits
    docs/lanes/                  evidence dossiers written by delegated lanes
    scripts/                     one script per artifact, with the rules it enforces
    src/aerarium/                the ingestion and grading package
    corpus/                      fetched source documents (gitignored, regenerable)

## Run it

    uv venv .venv && .venv/bin/python -m pip install -e .
    .venv/bin/aer sync && .venv/bin/aer ingest-budget && .venv/bin/aer ingest-recipients
    .venv/bin/aer ingest-partijfinanciering --giften-years 2019-2025
    .venv/bin/aer grade && .venv/bin/aer validate-party

    bash scripts/fetch_tk2025.sh
    .venv/bin/python scripts/ingest_tk2025.py
    .venv/bin/python scripts/ingest_tk2025_post.py
    .venv/bin/python scripts/extract_gifts.py
    .venv/bin/python scripts/redact_outputs.py
    .venv/bin/python scripts/export_view.py          # 1. payload from the store
    .venv/bin/python scripts/classify_donors.py      # 2. derives from view-data.json
    .venv/bin/python scripts/export_view.py          # 3. re-export so the derivation lands
    .venv/bin/python scripts/reembed_view.py         # 4. inject the payload into the page
    .venv/bin/python scripts/gift_timing.py
    .venv/bin/python scripts/flow.py
    .venv/bin/python scripts/thinktanks.py
    .venv/bin/python scripts/classify_creditors.py
    .venv/bin/python scripts/donor_claims.py
    .venv/bin/python scripts/overshoots.py
    .venv/bin/python scripts/classify_rekenkamer.py --titles
    .venv/bin/python scripts/build_state_payload.py   # the page's state-side payload
    .venv/bin/python scripts/build_manifest.py
    .venv/bin/python scripts/verify_bindings.py      # 177 bound values: prose parsed, numbers recomputed,
                                                     # the page executed under node, canary trips on demand

Order matters in one place: `classify_donors.py` reads `view-data.json`, so the export runs twice. A pipeline that
skips the second pass only ever worked because a stale file was on disk.

The report corpus is fetched with `scripts/fetch_corpus.sh` (92 documents) and the Rekenkamer corpus with
`scripts/fetch_rekenkamer.py` (2.677 pages, one request per second; `--firecrawl-pages` when the host blocks the
direct path). Neither is mirrored here; see privacy.

## How the grading works

Six rungs, from appropriation to audit finding, in `docs/GRADING.md`. A euro's grade is how far down it survives:
`documented`, `named`, `partial`, `aggregate-only`, `absent`, `not-published`. The vocabulary is closed and is not
paraphrased anywhere in this repository.

The chain joins at **chapter × instrument type**, not at article: the two registers use the same words for
different grains, and `recipient_line.artikel` mixes article and article-onderdeel names (`PROBE-010`). Anything
graded from an article-level join would be a number about nothing.

## Rules this repository holds itself to

- A ceiling is not a payment, and an aggregate is not a flow.
- Absence is not zero. An empty page is `no-data-published`, never €0.
- A series that renames a category without saying so is a lie told in a chart.
- A balance is not a floor, and a percentage whose numerator and denominator cover different periods is not a share.
- No motive is inferred. The registers record transactions; where a reason is documented, it is quoted and attributed.
- Every figure a finding asserts is bound in `scripts/verify_bindings.py`: the number is parsed out of the prose,
  recomputed from the artifact, and the run fails when they disagree. It also executes the published page under
  node, because a correct payload is not a working page. It covers the claims listed in that file, not every
  number in the tree, and `--canary` perturbs one value to prove the checker can fail.
- Every artifact names its producer, or is declared `CURATED` with a reason, in `docs/MANIFEST.md`.

## Privacy

The gift register publishes each donor's street address. Names, amounts, dates and recipients are what the Wfpp
publishes those contributions *for*, so they are here. Street addresses and the UBO's place of residence are not,
because a public list of "person + home address + political donation" is a target list and nothing in this analysis
needs one. `out/gifts_donors.csv` keeps the full rows on the machine that built it.

The report corpus is likewise not mirrored: some of those documents quote a donor's address because the law requires
it, and indexing 92 of them together is a different act from the state publishing them one at a time.

## Data

Rijksfinancien open data is CC-0. `partijfinanciering.nl` prints no licence statement; publication of that data is
required by statute, not licensed as open data, and it is not described as CC-0 here. Rekenkamer publication pages
state no licence either; the corpus is used for classification and is not republished.

## Why this repository exists

See `NAME-AND-PERSONA.md`. For what each document is, start at `docs/INDEX.md`.
