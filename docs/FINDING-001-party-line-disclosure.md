# FINDING 001 — party line disclosure, 2016-2026

Artifact: `out/party-line-disclosure.csv` (27 rows, 28 columns). Regenerate with `.venv/bin/aer grade`;
check with `.venv/bin/aer validate` and `.venv/bin/python -m pytest -q tests/`. Figures are copied from
that CSV or from `docs/PROBE-001-what-the-sources-return.md`. Amounts in € thousand.

## Where the chain stops

Six rungs: appropriation (r1), ceiling and amendments (r2), instrument (r3), recipient (r4), realisation
(r5), audit finding (r6).

r1 and r3 hold every year 2016-2026. r5 holds every year except 2026, whose jaarverslag does not exist.
**r2 holds in no year:** the API declares `O1` and `O2` and serves neither, returning the unfiltered set
for both, exactly as for an invalid value. No amendment to the ceiling can be read from this source, so
`ceiling_k` is the ontwerpbegroting and nothing else. r6 is not probed.

r4 moves, and it is graded in euros rather than in row labels:

| year | r4 | named | anonymised | realised |
|---|---|---|---|---|
| 2016 | not-published | — | — | 17.330 |
| 2017 | aggregate-only | 0 | 17.994 | 17.992 |
| 2018 | aggregate-only | 0 | 16.124 | 16.125 |
| 2019 | aggregate-only | 0 | 17.452 | 17.444 |
| 2020 | named | 23.777 | 0 | 23.770 |
| 2021 | partial | 27.011 | 636 | 27.646 |
| 2022 | partial | 5.340 | 22.109 | 27.456 |
| 2023 | partial | 5.137 | 24.321 | 29.458 |
| 2024 | partial | 4.510 | 0 | 33.923 |
| 2025 | not-published | — | — | 26.929 |
| 2026 | not-published | — | — | — |

One scheme, four publication practices in nine years: fully anonymised (2017-2019), fully named (2020),
a named remainder beside one anonymised row carrying the bulk (2021-2023), and a year where most of the
money sits in no row at all (2024). No announcement accompanies any of the four.

## The 2024 arithmetic

Named 4.510 of 33.923 realised. The remaining **29.413 is in no row**: not named, not anonymised,
absent. Named coverage 13,3%. Four columns carry four quantities, `ceiling_k` 30.719, `realised_k`
33.923, `named_k` 4.510, `anon_k` 0, and none is summed into another. A ceiling is not a payment and a
recipient sum is not a ceiling total. Twenty named party rows cover less than a seventh of the money.

## The rename

The budget tables call the line `Politieke partijen` in every year. The register calls it `Subsidiering
wet Financiering Politieke Partijen` in 2017 and 2018 only, and `Politieke partijen` from 2019. Same
money: 2017 register 17.994 against realisation 17.992, 2018 16.124 against 16.125. The family carries
both names, so the rename stays visible in `register_names` rather than folded away.

## 2025 and 2026

2025 realisation 26.929 against a ceiling of 32.910. The row-level register stops at budget year 2024 and
its dataset page still serves only the 2017-2024 file, so 2025 and 2026 are `not-published`: measured,
not estimated. 2026 carries a ceiling of 32.232 and no jaarverslag.

## Elsewhere in the neighbourhood

`Decentrale politieke partijen`, 2025: ceiling 8.382, realisation 0. `documented-zero`, a reportable
state, not a missing value.

`NFRP Politieke Partijen` (chapter V, Buitenlandse Zaken) is register-only: the begroting names the
parent programme `Nederlands Fonds voor Regionale Partnerschappen MATRA` and does not split out the party
sub-scheme, so r1 is `not-separable` and reach 0. The register splits it: 2018 anonymised 462, 2019
anonymised 540, 2020 six named rows 22 plus 3 anonymised, 2023 twenty named rows 1.362 plus 138
anonymised, 2024 twenty named rows 1.905 plus 25 anonymised. Those named recipients are the parties'
international foundations, with KvK numbers. They are the one category of neveninstelling this register
names; the scientific institutes appear in no row.

## What the join cannot do

The chart endpoints return aggregates keyed by `id` alone, with no edge between scheme and recipient.
That edge exists only in the 277.664-row bulk file, where identity is `lower(ontvanger)` plus KvK, and
KvK is blank on every anonymised row and on 13 of the 20 named party rows in 2024. Every merge resting on
a name is a decision to be recorded with its evidence.
