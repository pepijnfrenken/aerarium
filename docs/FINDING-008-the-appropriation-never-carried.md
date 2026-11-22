# Finding 008 — the €177bn the appropriation never carried

Vintage 2026-11-22. Store `data/aerarium.duckdb`, read-only. Join at chapter × instrument type as established
in `PROBE-010`. No euro is graded in this document; it fixes which euros *cannot* be graded from the
appropriation at all.

## What the join throws out

Joining the appropriation (all expenditure, `vuo='U'`) to the recipient register at chapter × instrument type
gives **575** year-groups. **533** sit at or below the budget figure. **42** exceed it by more than 2%, and the
obvious reading — a broken join — is the wrong one, because the 42 are not 42 separate problems.

| instrument type | groups over | overshoot |
|---|---:|---:|
| Bekostiging | 9 | **€ 102.592,4 m** |
| Bijdrage aan sociale fondsen | 4 | **€ 74.575,5 m** |
| Bijdrage aan medeoverheden | 6 | € 5.182,6 m |
| Bijdrage aan agentschappen | 7 | € 2.310,6 m |
| Bijdrage aan (andere) begrotingshoofdstukken | 9 | € 622,3 m |
| Bijdrage aan (inter-)nationale organisaties | 4 | € 444,6 m |
| Subsidies (regelingen) | 1 | € 437,3 m |
| Garanties | 1 | € 51,5 m |
| Leningen | 1 | € 3,8 m |

Two instrument types — **13 groups** — carry **€ 177.167,9 m** of the overshoot. The other **29 groups** carry
**€ 9.053,0 m** between them. So the question is not "why does the join overshoot in 42 places" but "what are
these two instrument types", and the answer is that they are not appropriation money.

## Bekostiging is paid by the Zorginstituut, not by the ministry

Chapter XVI in 2024:

- appropriation, `Bekostiging`: **€ 435.738 k**;
- recipient register, `Bekostiging`: **€ 24.419.057 k across 30 recipients** — a factor of 56.

The chapter's real appropriation instruments in 2024 are policy lines: `Geneeskundige geestelijke
gezondheidszorg` € 10.515,8 m, `Subsidies (regelingen)` € 5.499,4 m, `Geriatrische revalidatiezorg en
eerstelijnsverblijf` € 2.647,2 m. There is no large appropriation line called `Bekostiging` because the money
that enters the register under that name does not come from the appropriation — it flows through the
Zorginstituut from the zorgverzekeringsfonds and the Wlz.

The same shape appears in every year: 2017 € 1.238.790 k against € 7.078.205 k, 2020 € 424.506 k against
€ 12.541.132 k, 2023 € 297.919 k against € 32.246.736 k. The ratio moves with the care budget, not with the
join.

## Bijdrage aan sociale fondsen is the same shape

Chapter XV appropriates **€ 20.000 k** for `Bijdrage aan sociale fondsen` — in every year from 2018 to 2021 —
against a register showing:

| year | register | overshoot |
|---|---:|---:|
| 2018 | € 13.862.630 k | € 13.842,6 m |
| 2019 | € 17.436.873 k | € 17.416,9 m |
| 2020 | € 20.172.859 k | € 20.152,9 m |
| 2021 | € 23.183.151 k | € 23.163,2 m |

A symbolic €20 m appropriation beside €13–23 bn of recorded flows. In 2024 the register publishes no row for
that instrument under XV at all, and correspondingly that year does not overshoot — the register's coverage
moves, the appropriation line does not.

## Why this is a finding and not a bug

The join is doing what it should. It is telling us that **€ 177 bn of recipient money has no appropriation line
of the same name behind it**, because it is not appropriated money: it is premium- and fund-financed. That is the
same basis break `PROBE-006` found at chapter level and `flow.py` now refuses to harmonise across, seen here at
the instrument grain with the euro amounts attached.

The consequence for grading is concrete. A euro of `Bekostiging` paid to a named care provider reaches a named
recipient (r4) but it does **not** satisfy the chain from an appropriation (r1→r2→r3). Grading it as though the
appropriation carried it would put a €24 bn flow behind a €436 m line. These euros need their own grade:
*recorded at the recipient, financed outside the appropriation* — visible where they land, invisible in the
budget.

## What remains genuinely unexplained: 29 groups, € 9.053,0 m

The larger of the residual cases, each of which is a real booking difference or a key collision and each of
which can be named:

- **VI, 2022, `Bijdrage aan medeoverheden`** — € 1.634,1 m over. Justice money spent by municipalities and
  police regions is the expected shape here.
- **A, 2018, `Bijdrage aan agentschappen`** — € 1.625,9 m over.
- **XII, 2019 and 2020, `Bijdrage aan medeoverheden`** — € 926,5 m and € 922,5 m.

€9 bn across 29 groups is tractable, and it is the next piece of work. Until each is either explained by a
documented booking rule or shown to be a collision, no euro is graded.

## What is not claimed here

- The **mechanism** for sociale fondsen (premie, volksverzekeringen, a specific fonds) is inferred from the
  mismatch and from the statutory financing of the fondsen; no document in this store states it. The
  **arithmetic** is measured; the mechanism is labelled.
- The **XVII BHOS ODA** question stands where `PROBE-006` left it: unresolved, needing a scheme-level crosswalk.
- Nothing here says any recipient was overpaid. A register showing more money under an instrument than the
  appropriation line carries means the money came from somewhere else, not that someone received too much.
