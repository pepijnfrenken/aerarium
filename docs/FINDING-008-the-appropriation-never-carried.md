# Finding 008 — the €178bn the appropriation never carried

Vintage 2026-11-28. Store `data/aerarium.duckdb`, read-only. Join at chapter × instrument type. No euro is graded in
this document; it fixes which euros *cannot* be graded from the appropriation at all.

**Correction, 2026-11-28 — this supersedes every figure in the first version.** That version published
**€ 177.167,9 m across 13 groups**. It added the draft budget (`fase='OWB'`) to the realised account (`fase='JV'`)
and called the sum an appropriation: chapter XVI 2024 `Bekostiging` read as € 435.738 k because € 235.885 k of draft
had been added to € 199.853 k of realised. The recipient register records payments actually made, so the comparator
is the realised account. On that basis the figure is **€ 178.462,2 m across 18 groups**, and every number below is
the corrected one. `out/overshoots.json` keeps the all-phase sum only under `diagnostic_all_phases`, labelled as not
a comparator.

## What the join throws out

Comparing the realised appropriation to the recipient register at chapter × instrument type gives **567**
year-groups. **328** sit at or below the appropriation, **143** sit above it but inside the 2% tolerance, and **96**
exceed it by more than 2%. The obvious reading of 96 — a broken join — is the wrong one, because they are not 96
separate problems:

| instrument type | groups over | overshoot |
|---|---:|---:|
| Bekostiging | 14 | **€ 103.846,7 m** |
| Bijdrage aan sociale fondsen | 4 | **€ 74.615,5 m** |
| the remaining 78 chapter-instrument-years | 78 | € 13.645,3 m |

Two instrument types — **18 groups** — carry **€ 178.462,2 m** of the overshoot. The question is not "why does the
join overshoot in 96 places" but "what are these two instrument types", and the answer is that they are not
appropriation money.

## Bekostiging is paid by the Zorginstituut, not by the ministry

Chapter XVI in 2024:

- realised appropriation (`JV`), `Bekostiging`: **€ 199.853 k**;
- draft appropriation (`OWB`), same line: € 235.885 k — a different quantity, never added to the realised figure;
- recipient register, `Bekostiging`: **€ 24.419.057 k across 30 distinct recipient spellings**.

The chapter's real appropriation instruments in 2024 are policy lines: `Geneeskundige geestelijke gezondheidszorg`
€ 10.515,8 m, `Subsidies (regelingen)` € 5.499,4 m, `Geriatrische revalidatiezorg en eerstelijnsverblijf` € 2.647,2 m.
There is no large appropriation line called `Bekostiging` because the money entering the register under that name
does not come from the appropriation: it flows through the Zorginstituut from the zorgverzekeringsfonds and the Wlz.

The same shape recurs in 2017, 2019, 2020, 2021 and 2023 — 2023 runs € 245.411 k realised against € 32.246.736 k in
the register. It is **not** every year: in 2022 XVI carries € 413.627 k on the line and the register has no
`Bekostiging` row at all, which is a coverage gap, not a reconciliation.

## Bijdrage aan sociale fondsen is the same shape

Chapter XV appropriates **€ 10.000 k** on this line in *each* phase, in each of 2018–2021, against a register
showing:

| year | realised appropriation | register |
|---|---:|---:|
| 2018 | € 10.000 k | € 13.862.630 k |
| 2019 | € 10.000 k | € 17.436.873 k |
| 2020 | € 10.000 k | € 20.172.859 k |
| 2021 | € 10.000 k | € 23.183.151 k |

From 2022 to 2024 the appropriation line stays at € 10.000 k and the register publishes **no row** for the
instrument, so those years cannot be compared at all. The register's coverage moves; the appropriation does not.

## Why this is a finding and not a bug

The join is doing what it should. It is telling us that **€ 178,5 bn of recipient money has no realised
appropriation line of the same name behind it**, because it is not appropriated money. That is the same
financing-basis break `PROBE-006` found at chapter level, seen here at the instrument grain with the euro amounts
attached.

The consequence for grading is concrete. A euro of `Bekostiging` paid to a named care provider reaches a named
recipient (r4) but it does **not** satisfy the chain from an appropriation (r1→r2→r3). Grading it as though the
appropriation carried it would put a € 24 bn flow behind a € 200 m line. These euros need their own grade:
*recorded at the recipient, financed outside the appropriation* — visible where they land, invisible in the budget.

## What remains genuinely unexplained: 78 groups, € 13.645,3 m

Of those, **35** sit in a chapter-year that carries a positive appropriation on `Bijdrage aan (andere)
begrotingshoofdstukken`, and **43** have no such line. Neither is an explanation. The transfer line's presence does
not trace an edge to the group, and four of the 35 are overshoots **on** the transfer instrument itself, which a
transfer cannot explain.

Two of the largest rows without any transfer line:

- **VI 2022, `Bijdrage aan medeoverheden`** — € 1.634.121 k over.
- **A 2018, `Bijdrage aan agentschappen`** — € 1.625.872 k over.

## What is not claimed here

- The **mechanism** for sociale fondsen (premie, volksverzekeringen, a specific fonds) is inferred from the mismatch
  and from the statutory financing of the fondsen; no document in this store states it. The **arithmetic** is
  measured; the mechanism is labelled.
- That these groups are errors, or that each is a booking difference or a key collision. That framing was published
  here and is withdrawn: 35 of the 78 share a chapter-year with a transfer line and 43 have nothing.
- The **XVII BHOS ODA** question stands where `PROBE-006` left it: unresolved, needing a scheme-level crosswalk.
- Nothing here says any recipient was overpaid. A register showing more money under an instrument than the
  appropriation carries means the money came from somewhere else, not that someone received too much.
