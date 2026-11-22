# Probe 010 — where the two registers actually join

Vintage 2026-11-22, `data/aerarium.duckdb`, read-only. No artifact yet: this probe establishes the join keys
before any euro is graded, because a join built on the wrong key produces a confident number about nothing.

## The schema says the two tables describe the same things. They do not.

`PROBE-006` concluded the r3→r4 edge is instrument-level and not a decomposition of chapter totals. Taking that
literally, the next step was a join on `(hoofdstuk, artikel, instrument, regeling)`. That join cannot be built as
written, because the two tables use the same words for different grains.

| field | `budget_line` | `recipient_line` |
|---|---|---|
| chapter | `hoofdstuk_nummer` (e.g. `I`) | `hoofdstuk` (e.g. `A`) |
| article | `artikel_nummer` (`2`) and `artikel_naam` | `artikel` — **a name**, e.g. `Hoofdwegennet` |
| article part | `artikelonderdeel_nummer` / `_naam` | `detail` |
| instrument | `instrument_naam`, **286 distinct values** | `instrument`, **11 distinct values** |
| scheme | `regeling_naam` | `regeling` |

Distinct keys at the full four-field grain: **28.391** on the budget side against **8.795** in the recipient
register. A join across them is not a join; it is a filter that keeps whatever happens to collide.

## What "instrument" means on each side

The budget's `instrument_naam` is mostly a **policy instrument**: `Functionele uitgaven van de Koning`,
`Grondwettelijke uitkering aan de leden vh Koninklijk Huis`. It has 286 distinct values.

The recipient register's `instrument` is an **instrument type**: **ten named types**, plus a blank that is not a type at all but still carries **974 recipients and €224 m**:

| instrument type | recipients | € m |
|---|---:|---:|
| Bekostiging | 2.133 | 423.259 |
| Bijdrage aan medeoverheden | 2.015 | 359.220 |
| Bijdrage aan ZBOs en RWTs | 1.026 | 165.513 |
| Subsidies (regelingen) | 130.701 | 108.803 |
| Bijdrage aan sociale fondsen | 23 | 87.082 |
| Bijdrage aan (inter-)nationale organisaties | 2.246 | 71.329 |
| Bijdrage aan agentschappen | 392 | 51.410 |
| Leningen | 484 | 40.093 |
| Bijdrage aan (andere) begrotingshoofdstukken | 102 | 26.949 |
| Garanties | 485 | 1.045 |
| *(blank)* | 974 | 224 |

Nine of those eleven strings also appear as `instrument_naam` in the budget, on **24.391 rows carrying
€3.380.951 m of the €7.392.472 m** of expenditure in the store (45,7%). The other 55,3% of budget lines are
labelled with policy instruments that the recipient register never uses, so **no recipient row can be expected
to sit under them** — and their absence from the register is not a disclosure failure, it is a naming difference.

That distinction matters more than the join itself. A reachability measure that counts those rows as "money that
stopped at rung 3" is measuring vocabulary, not disclosure.

## The article field cannot carry the join

`recipient_line.artikel` has **238 distinct values**, of which **160 match an `artikel_naam`** and **70 match an
`artikelonderdeel_naam`**. So the recipient register writes the article field at two different grains depending on
the line, without saying which. Joining on `artikel` alone therefore drops or double-counts depending on the year
and the chapter, and any per-article figure built on it inherits that.

This is why the join is built one level up.

## The join that can be built

Chapter × instrument type, over budget (all expenditure) and recipient money:

- **575** chapter-instrument-type-year groups join;
- **533** (92,7%) have recipient money at or below the budget figure;
- **42** exceed it by more than 2%.

42 overshoots at this grain is a tractable number: each one is either a real booking difference (money recorded
under a neighbour chapter, a shared instrument) or a key collision, and each can be named. That work is next, and
until it is done no euro is graded.

## What this changes

The chain's join point is **chapter × instrument type**, with `regeling` as a refinement where both sides print
the same scheme name. It is not an article-level join, and the article-level version published earlier in this
project's own planning was not buildable. The r2 rung is untouched by this and remains the weakest link.
