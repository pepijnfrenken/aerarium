# AERARIUM

Two ledgers the Dutch state publishes separately: what political parties and their neveninstellingen receive, and
what the state pays out. There is no shared identifier between them. This repository builds the join, and grades
every euro by how far along the chain it can still be followed.

**[Read the ledger →](https://pepijnfrenken.github.io/aerarium/)**

## What it does

The register tells you a party got money. It does not tell you who gave it, what an entity is for, or whether the
money arrived before an election. AERARIUM joins four published sources:

| source | what it gives |
|---|---|
| Rijksfinancien open data (CC-0) | the party line in chapter VII, ceiling and realisation, per year |
| Rijksfinancien register | named recipients, chapter V NFRP foundations with KvK |
| Dashboard partijfinanciering (BZK) | subsidy paid per party; every contribution of €1.000+ with donor and date |
| the parties' own Wfpp reports | the per-entity split, the neveninstellingen list, the spending |

Every figure carries its source, its vintage and the document that holds it. Where a chain breaks, the break is
the finding.

## Headline results

- **2.301 donors, €25.038.264,64** in contributions 2022-2024, every party-year reconciled to the euro before use.
- **Gift money is 75% individuals, 19% entities, 3% bequests, 3% party vehicles.** Entity share ranges from 0,0%
  (SP) and 0,3% (GL) to 79,9% (BVNL) and 72,2% (SGP): two different systems, not a gradient.
- **The largest "donors" are the parties.** VVD's biggest is VVD: €1.810.000 of its €3.592.775 in 2023 came from its
  own foundations. SP's and GL's biggest are their own elected representatives under a salary-transfer rule.
- **GroenLinks and PvdA are one party now (PRO).** Read together they are the largest organisation in the window:
  €20.529.188 against VVD's €19.554.840.
- **Donations cluster in campaign windows.** €1.135.143 of 2023's gift money arrived in the 90 days before the
  22 November election, 1,75× the same window a year earlier. For CDA 95,4% of the year's donations landed there;
  for SP 28,3%, because SP's money is salary transfers, not campaigns.
- **The state side stops at the party.** 2024: 20 parties named, €4.510k attributed, €29.413k in no register row at
  all. Only 10 of 92 annual reports state the per-entity split.
- **NFRP**: a single anonymised row for 2018 and 2019, nothing at all for 2021-2022, then full itemisation for
  2023-2024. 46 rows in 19 spellings collapse to 11 entities by KvK.

## Layout

    out/index.html               the ledger page: self-contained, no network, renders from file://
    out/view-data.json           everything the page draws, with source ids
    out/gifts_donors_public.csv  donor rows, no addresses
    out/neveninstellingen.csv    242 rows: entities named by each party in its own report
    out/donor-typology.json      2.301 donors in four classes
    out/party-lineage.json       when a name stopped meaning the same party
    out/gift-timing.json         donations by date, against election days
    docs/                        probes, findings, grading vocabulary
    scripts/                     one script per artifact, with the rules it enforces
    src/aerarium/                the ingestion and grading package

## Run it

    uv venv .venv && .venv/bin/python -m pip install -e .
    .venv/bin/aer sync && .venv/bin/aer ingest-budget && .venv/bin/aer ingest-recipients
    .venv/bin/aer ingest-partijfinanciering --giften-years 2019-2025
    .venv/bin/aer grade && .venv/bin/aer validate-party

    .venv/bin/python scripts/extract_gifts.py
    .venv/bin/python scripts/redact_outputs.py
    .venv/bin/python scripts/export_view.py
    .venv/bin/python scripts/reembed_view.py
    .venv/bin/python scripts/classify_donors.py
    .venv/bin/python scripts/gift_timing.py
    .venv/bin/python scripts/verify_findings.py     # 71 assertions on the prose

The report corpus is fetched with `scripts/fetch_corpus.sh` (92 documents). It is not mirrored here; see privacy.

## How the grading works

Six rungs, from appropriation to audit finding, in `docs/GRADING.md`. A euro's grade is how far down it survives:
`documented`, `named`, `partial`, `aggregate-only`, `absent`, `not-published`. The vocabulary is closed and is not
paraphrased anywhere in this repository.

## Rules this repository holds itself to

- A ceiling is not a payment, and an aggregate is not a flow.
- Absence is not zero. An empty page is `no-data-published`, never €0.
- A series that renames a category without saying so is a lie told in a chart.
- No motive is inferred. The registers record transactions; where a reason is documented, it is quoted and attributed.
- Every number in a finding is asserted by `scripts/verify_findings.py`, which fails when prose and data drift apart.

## Privacy

The gift register publishes each donor's street address. Names, amounts, dates and recipients are what the Wfpp
publishes those contributions *for*, so they are here. Street addresses and the UBO's place of residence are not,
because a public list of "person + home address + political donation" is a target list and nothing in this analysis
needs one. `out/gifts_donors.csv` keeps the full rows on the machine that built it.

The report corpus is likewise not mirrored: some of those documents quote a donor's address because the law requires
it, and indexing 92 of them together is a different act from the state publishing them one at a time.

## Data

Rijksfinancien open data is CC-0. `partijfinanciering.nl` prints no licence statement; publication of that data is
required by statute, not licensed as open data, and it is not described as CC-0 here.

## Built on the AIWG scaffold

`.aiwg/`, `AIWG.md` and `CLAUDE.md` are the framework's, not the project's. See `NAME-AND-PERSONA.md` for why this
repository exists and `docs/` for what it found.
