# PROBE 004 — the neveninstellingen each party names in its own report

`scripts/extract_neveninstellingen.py` over `corpus/text/` (92 reports, 2020-2024). Output:
`out/neveninstellingen.csv`, 242 rows, 120 distinct names, 127 rows carrying an amount. Retrieved 2026-11-20.

This is the step the Rijksregister cannot do: the register stops at the party, and the party's own report is
where the per-entity split lives. It is the only place in the chain where a party names what its scientific
institute, youth wing or foreign foundation received.

## What the extraction found

| year | rows | of which with an amount |
|---|---|---|
| 2020 | 30 | 17 |
| 2021 | 39 | 21 |
| 2022 | 39 | 21 |
| 2023 | 67 | 35 |
| 2024 | 67 | 33 |

17 of 21 parties name at least one entity. Four name nothing that survived extraction: 50PLUS, BBB, BIJ1, BVNL.
50PLUS is a recall failure rather than a disclosure gap — it does name `het Wetenschappelijk Instituut` and the
`Jan Nagel Foundation` in prose, which the name filter rejected.

## Three presentation shapes, and what each yields

- **Bullet list.** VVD 2024: `Daarnaast is er een overzicht van giften en schulden bijgevoegd van de
  neveninstellingen van de VVD:` then `- Stichting Ivo Opstelten Foundation;` and two more. Names only, no
  figures in the list.
- **Amount table.** CDA 2024: `De totaalbedragen van de uitgegeven subsidie per entiteit zijn:` then a name and a
  euro amount per line. Names and figures.
- **Inline figure.** `Stichting Huisvesting CDA   603.243` — a bullet whose figure sits on the same line.

## Verification

Four rows checked against the CDA 2020 table, which reads in the source as:

    Stichting Wetenschappelijk Instituut voor het CDA      832.280
    Stichting Huisvesting CDA                              603.243
    CDA-Bestuurdersvereniging                               91.940
    Vereniging CDJA                                        220.462
    CDAV                                                    51.173
    Overige                                                107.922
    Totaal Rekening courant neveninstellingen            1.907.020

All four were extracted exactly. `Overige` and `Totaal` were correctly refused as non-entities.

## The amount is not always a subsidy

The CDA figures above sum to a line the report labels `Totaal Rekening courant neveninstellingen` — an
intercompany current-account balance, not a subsidy allocation. The column is therefore `bedrag_eur` and means
"the amount the report attributes to that entity", nothing more. Do not read it as subsidy without checking the
heading it came from. The evidence quote preserves that heading.

## Known limits of this extraction

- **Bare acronyms are missed.** `CDAV` (€51.173) fails the name filter because it carries no organisational noun.
  Recall is deliberately sacrificed for precision: an earlier pass without the filter produced 777 rows of Dutch
  sentence fragments.
- **Compound listings stay compound.** `DWARS, Wetenschappelijk Bureau GroenLinks en Stichting Bureau de Helling`
  is one row, as published. Splitting it would be a judgement the document does not make.
- **Duplicate spellings are not merged.** The PvdA's institute appears as `Wiardi Beckman Stichting (WBS)`,
  `Wiardi Beckmanstichting` and `Wiardi Beckman Stichting`. Same for `Eduardo Freistichting` versus the register's
  `Eduardo Frei Stichting`, and `Fondsenwervinq` with a `q` from the PDF text layer. Per the project rule, an
  entity total across years is a decision about these strings and belongs in an adjudication ledger.
- **Two figures on one line are refused, not guessed.** Budget-versus-actual columns leave nothing in the line
  saying which is which, so the row keeps the name and drops the amount.
- **A few sub-€10 amounts survive.** They are page numbers or stray digits near a table. They are visible in
  `bedrag_eur` and were not deleted, because silent deletion is how a dataset starts lying.
- **Party keys are canonicalised, filenames are not.** `FVD`→`FvD`, `GroenLinks`→`GL`, `ChristenUnie`→`CU`,
  `50plus`→`50PLUS`, because the register spells one party differently across years. The raw string is
  recoverable from `bron_bestand`.

## What this does not establish

An entity named with an amount is not necessarily an entity that received state subsidy: the report may be
showing a loan, a current account, or a combined figure. Nor does naming imply the money reached the entity —
Wfpp art. 9 makes the party pass the earmarked amount through one-for-one, and VVD's own report calls itself
`een doorgeefluik`. The extraction establishes what each party published about its own entities, which is
exactly as far as this rung goes.
