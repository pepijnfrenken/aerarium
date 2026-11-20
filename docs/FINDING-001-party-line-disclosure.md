# FINDING 001 — party line disclosure, 2016-2026

Graded from the Tabularium store this session. Commands run: `aer grade`, `aer validate`,
`.venv/bin/python -m pytest -q tests/`. The artifact is `out/party-line-disclosure.csv`
(27 data rows, 28-column header). Every figure below is copied from that CSV or from
`docs/PROBE-001-what-the-sources-return.md`; nothing is estimated. The pipeline commands listed
above are the ones that produced it.

The chain, and where it stops
-----------------------------

Six rungs, in order: appropriation, ceiling and amendments, instrument, recipient, realisation,
audit finding. The grade of a euro is how far along that chain it can be followed. For the party
line the walk reaches r1, r2, r3 and r5 in every year. It never reaches r4 or r6. Three reasons,
and they are the finding:

1. **r4 is measured in euros, not in row labels.** A register publishes 20 named rows in 2024
   totalling €4,510k. A row label is not a payment. Named 13.3% of the realisation is the grade;
   "20 named recipients" would be a label wearing a number.
2. **The budget and the register do not even agree on the labelling.** 2016-2026, budget tables
   call the line *Politieke partijen*; the register calls it *Subsidiering wet Financiering
   Politieke Partijen*. Same money, different name; the two reconcile to within 2k (2017: -2;
   2018: +1). Drift is evidence, not noise. The family carries both names.
3. **An aggregate is not a flow.** `hoofdstukken` is a sum over all years and cannot be split into
   a yearly series. The 8,241 regelingen and 277,664 row-level records are chart inputs, not flows
   you can reconcile against.
4. **No key exists between the two halves.** The chart API returns aggregates keyed by id alone.
   The Unmapped register (141,840k and 102,002k) is what remains after the party neighbourhoods
   are scoped out — an inventory of what the join does not cover yet, reported, not dropped.

The 2024 arithmetic
-------------------

Named 4,510 of 33,923 realised, so 29,413 unnamed — 13.3% coverage of the annual realisation.
Four separate columns: `ceiling_k` 30,719, `realised_k` 33,923, `named_k` 4,510, `anon_k` 0.
A ceiling is not a payment; the recipient sum is not a ceiling total. None of the three is summed
into another anywhere.

The 2019 aggregate-only year and the 2020-2021 named years
----------------------------------------------------------

2019: named 0, anonymised 17,452. 2020: named 23,777 across 12 rows. 2021: named 27,011 across 15
rows, one anonymised row of 636. The register publishes named in 2020 and 2021, aggregate-only in
2019, and partial — a named remainder plus one anonymised row carrying the bulk — in 2022 and 2023.

The 2017/2018 rename
--------------------

The budget calls the line *Politieke partijen*; the register calls it *Subsidiering wet
Financiering Politieke Partijen*. Same money, different label.

The 2025/2026 state
-------------------

Realisation 26,929 for 2025. The row-level register is not published past 2024, so the 2025 and
2026 r4 grades are *not-published* — a measured state, not an estimate.

Where the walk stops elsewhere
------------------------------

`Decentrale politieke partijen`, 2025: ceiling 8,382, realised 0 — documented-zero, a reportable
state, not a missing value. Chapter VII 2026 carries 358 budget rows in one call. The NFRP
programme lines (2018: 462; 2019: 540; 2020: 22; 2023: 138; 2024: 25) are register-only: the
begroting names the parent programme and does not split out the sub-scheme, so there is no ceiling
to grade at r1, and the rung is named accordingly.
