# FINDING 003 — who donates, and what the register will not tell you

From the dashboard's donor-level gift rows, 2022-2024: 2.301 donors, €25.038.264,64, every party-year
reconciled to the published total. The question asked was why these entities give. The register has no field
for that, and this finding does not invent one. What follows separates what is published, what can be counted,
and what is either a stated motive or nothing.

## The register records a transaction, not a reason

Per contribution it publishes: the donor's name, the donor's address, the amount above €1.000, the date, the
receiving party or neveninstelling, and — for 137 rows — the UBO behind the donor. It publishes no purpose, no
sector, no interest, no contact, no counterpart. A €150.000 gift from a B.V. and a €150.000 gift from an MPC
are the same row with a different name.

So the answer to "why" is not in this source, and any figure below is about *what* the donors are, not why.

## What the donor population is made of

Classified by name and by the register's own entity tags, 2.301 donors (money rounded to whole euros; the
underlying figures carry cents and are in `out/donor-typology.json`):

| class | donors | money | share |
|---|---|---|---|
| individual | 2.089 | €18.809.057 | 75,1% |
| entity (company, holding, foundation, fund) | 194 | €4.827.459 | 19,3% |
| bequest (nalatenschap, erven, p/a notaris) | 13 | €698.798 | 2,8% |
| party vehicle (a foundation of the receiving party itself) | 5 | €702.950 | 2,8% |

Per party, the split is not a gradient, it is two different systems:

| party | total gifts | individuals | entities | bequests | entity share |
|---|---|---|---|---|---|
| GL | 6.413.924 | 6.393.924 | 20.000 | 0 | 0,3% |
| SP | 6.229.126 | 6.146.746 | 1.812 | 80.568 | 0,0% |
| VVD | 4.349.220 | 960.438 | 2.699.832 | 0 | 62,1% |
| D66 | 1.594.513 | 1.181.922 | 412.591 | 0 | 25,9% |
| PvdA | 1.359.481 | 1.270.946 | 20.000 | 68.535 | 1,5% |
| PvdD | 1.339.077 | 744.382 | 45.000 | 549.695 | 3,4% |
| CDA | 923.705 | 655.125 | 268.580 | 0 | 29,1% |
| Volt | 648.734 | 313.195 | 335.539 | 0 | 51,7% |
| FvD | 596.116 | 273.348 | 322.768 | 0 | 54,1% |
| CU | 536.654 | 441.214 | 81.440 | 0 | 15,2% |
| SGP | 336.482 | 93.519 | 242.963 | 0 | 72,2% |
| BVNL | 256.465 | 51.464 | 205.001 | 0 | 79,9% |
| BBB | 164.633 | 70.200 | 94.433 | 0 | 57,4% |
| JA21 | 99.580 | 37.080 | 62.500 | 0 | 62,8% |
| DENK | 70.106 | 70.106 | 0 | 0 | 0,0% |
| NSC | 68.649 | 68.649 | 0 | 0 | 0,0% |
| PVV | 50.000 | 35.000 | 15.000 | 0 | 30,0% |
| OPNL | 1.800 | 1.800 | 0 | 0 | 0,0% |

The table covers all **eighteen** filers with a positive gift total, including CU and OPNL; twenty-one parties
filed in the register, and 50PLUS, BIJ1 and Goud filed with no positive gift money. An earlier version said
nineteen, which was simply wrong, and an earlier version
omitted both without saying why, which made the ranking beside it look better supported than it was. CU's
entity money is €81.440 and its €14.000 party vehicle is classified separately, so its organisational share is
15,2% on the entity class alone — 17,8% (€95.440 of €536.654) if the vehicle is counted with it. An earlier
version of this paragraph put the vehicle inside the entity figure, which it is not, and the difference matters:
a vehicle is the party's own fundraising body, an entity is outside money. The
entity column alone.

GL, SP, PvdA, DENK and NSC take effectively no organisational money. VVD, BVNL, SGP, JA21, BBB, FvD and Volt
take most of theirs from organisations. That divide is real and it is counted, not assumed.

## The two reasons the third column is misleading on its own

**One: for GL, SP and PvdA the largest "donors" are their own elected representatives.** These parties operate
a salary-transfer rule — `afdracht` — under which representatives pay part or all of their political allowance
to the party. The SP requires the entire allowance and pays a modal salary back; GroenLinks and PvdA a fixed
percentage, with removal from the party for non-payment. VVD and CDA have no such rule. The SP's own site
states the arrangement and its purpose: independence from companies and large donors.

The register does not label these transfers, so they appear as gifts from individuals. For GroenLinks the
chain closes exactly. Its 2022 report has a table headed `Bijdragen 2022 Stichting GroenLinks in de Europese
Unie`, listing three contributions: Eickhout €58.553, Strik €66.778, Van Sparrentak €83.168. They sum to
€208.499, which is precisely what the register attributes to GroenLinks in de Europese Unie for 2022. The same
three also paid €30.319,66 to the party itself that year (Van Sparrentak €15.171,84, Eickhout €15.147,82), so
their total to the GroenLinks family in 2022 is €238.818,66. Two documents, no shared key, the same figure to
the euro on the foundation.

**Two: for VVD the largest "donor" is VVD.** The register prints the party's campaign foundation in more than one
spelling — `Stichting VVD Ondersteuning Tweede Kamerverkiezing,`, `Stichting Ondersteuning VVD Tweede
Kamerverkiezing,` and `Stichting Ondersteuning VVD Tweede Kamer-verkiezing (SOV)` all appear, including as a
third-party payee name on the same rows. Treating the variants as separate foundations and adding them counts one
organisation twice. As **one** entity, SOV gave the party **€1.600.000** across the window (€1.300.000 in 2023,
€300.000 in 2022). Beside it sit Stichting Het Thorbeckefonds (€350.000) and Stichting Ivo Opstelten Foundation
(€160.000), which are different legal persons and are listed separately for that reason, with the spelling
variants shown rather than merged.

All of them are named as VVD's own neveninstellingen in the party's 2024 report. SOV alone reports receiving
€1.244.932 in 2023 from third parties, and the party reports gifts from SOV. Those are two disclosures in two
documents; nothing in either register links a particular euro of the first to a particular euro of the second, so
the trail is *asserted by the filings and not traced*, and the €1.300.000 attributed to SOV in 2023 rests on merging
word-order variants of one name. The merge is a labelled claim with its basis stated, not an adjudication of
identity. Reading the party-level rows as outside money counts the same euros twice, and reading two spellings of
one foundation as two donors does it a third time.

So "gift share" is not a measure of outside influence. For SP and GL a large share of the money arrives from
their own elected representatives under a salary-transfer arrangement, so the ratio measures an internal rule more
than outside support; for VVD it measures the party's own fundraising vehicle. How much, exactly, is stated in the
entity shares above rather than in this sentence. The register cannot distinguish the three without
this outside reading, which is why the naive ranking is wrong in both directions.

## Bequests

Thirteen contributions are estates: €698.798 in total, and €549.695 of that went to PvdD, led by
`Nalatenschap M.A.J. Kooien - p/a Knook & Schot Notarissen` at €360.000 in 2022. A legacy is the one class of
donation where the donor cannot have a current commercial interest, and it is unusually concentrated in one
party. Nothing in the register says why someone left money to PvdD; the will is not published.

## The merged party does not look like either of its halves

GroenLinks and PvdA are one party since 2026-07-01 (PRO), so their donor profiles belong together. Combined
over 2022-2024: €7.773.405,02 in gifts, of which €40.000 from entities. That is 0,5% organisational money. An
earlier version of this line called it "the second lowest of any formation here", which the artifact does not
support: SP, DENK, NSC and OPNL are all recorded at 0,0%, so 0,5% ranks fifth, not second, and the comparison
set has to be stated for the rank to mean anything. What the number does show is that the merged formation is
overwhelmingly individual-funded, like both its halves. Reading the two rows as rival parties splits a single
fundraising base and makes both look smaller than the bloc is.

## Where a motive is actually documented

Three cases, and only because the donor or the reporting states it:

- **Steven Schuurman, via Stichting The Dreamery Foundation** (€240.000 across D66, GL, PvdA, 2022-2023; the
  register names the UBO as Schuurman). Tech entrepreneur. Stated reason, in his own words, on earlier giving:
  the climate crisis, and that D66's and PvdD's climate plans appealed to him "puur op de inhoud". He gave
  €1,25m to the German Greens in 2021. This is a donor stating a policy preference and acting on it. It is the
  clearest documented case in the data, and it is one donor.
- **W.J. van der Wind, via Movet Beheer** (CDA, €105.080 in the rows here). Prior reporting: €1,2m to CDA in
  2021, after which CDA put SME-friendly measures in its election programme; a leaked internal note suggested
  involvement in the leadership choice. The donation is in the register; the sequence is in the reporting. The
  causal claim is the journalists', not the register's.
- **SP's opposite case.** The SP states it accepts no gifts from companies or sponsors and funds itself from
  members and representatives. The register agrees: €1.812 of €6.229.126 is entity money, and that one row is
  a person whose surname contains "Groep".

## Lobbying: the second ledger is not there to join

The access side would be the natural counterpart to the money side: who these donors meet, on what subject.
No public national lobby register was found at the Tweede Kamer URLs tested (`/register-van-lobbyactiviteiten`,
`/lobby/register` both 404; `lobbyregister.tweedekamer.nl` does not resolve). Without it there is no register to
join a donor to a contact, and this repository will not manufacture one from press coverage.

The donors that are companies can be given a sector from their KvK registration, and their UBO from the
register's own field (134 distinct donor-UBO pairs). That yields a field, not a motive: a property developer
donating to a party that opposes a property tax is a hypothesis the documents do not test.

## Corrections this finding forces on earlier work

- **"Gift-dominant" was the wrong framing.** GL at 50,6% and SP at 52,0% gift share is mostly their own
  representatives' salary transfers. The composition table above replaces the ratio.
- **The 2023 VVD gift total of €3.592.775 includes €1.810.000 from VVD's own foundations** (2024: €327.495).
  Party-level gift totals are gross of internal movement, and are labelled that way from now on. An earlier
  version of this line assigned both amounts to 2024; the donor register puts them in 2023.
- **Of that €1.810.000, €1.300.000 rests on an inference, not a confirmed identity.** It comes from a name that
  is a word-order permutation of a VVD neveninstelling named in the party's own report, classified `entity`
  because the register does not tag it. Flagged and counted separately from the confirmed foundation donors.
  The euros are not shown to have been traced through both legs.
- **2025 is not unpublished, it is published elsewhere.** The dashboard's year page for 2025 renders empty, but
  BZK published a separate overview of gifts around the 2025 Tweede Kamer election, in two disjoint windows
  (`out/gifts-2025-election.json`, `out/gifts-2025-post-election.json`). Both are ingested and the page draws them;
  this note said "not ingested here" after that had stopped being true, which is the correction.
- **One VVD donation of €1.300.000 comes from a name that is a word-order permutation of a VVD neveninstelling
  named in the party's own report.** It is classified `entity`, not `party_vehicle`, because the register does
  not tag it and the identity is an inference. Flagged, not merged.
