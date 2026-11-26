# FINDING 004 — party spending cannot be compared across parties from these documents

Asked for spending next to income, to see whether election years cost more than the donations that paid for them.
The money is in the reports. It is not comparable, and that is the finding.

## What is there

131 campaign-spend lines across the 92 financial reports for 2020-2024, in `out/spending-campaign.csv`, each with
the line as printed. Three shapes at least:

    VVD 2023   Verkiezingscampagne      22 1.050.000 4.675.900 3.790.634
    GL  2023   I. Activiteiten ... campagne    E 836.285     EUR 2.861.445
    various    verkiezingscampagne                                  2.861.445

The first carries three amounts (plus a note number), the second two, the third one. Nothing in the documents
declares which column is budget and which is realised, and the parties do not share a template.

## What breaks

Reading the second amount as the realised figure — the layout CDA and GL use — gives 42 lines across 31
party-years. But:

- **10 of those 31 party-years produce conflicting values.** D66 2024 yields both €3.604.671 and €5.801.168 from
  different tables that both label a campaign line. PvdD 2020 yields €10.000 and €829.291. VVD 2023 yields
  €1.000.000 and €333.160, which is a sub-item and a total.
- **30 lines carry a single amount** and never say whether it is budget or actual.
- **59 lines carry three or more** amounts and cannot be resolved by position at all.

So the maximum defensible output is 21 party-years with a single consistent pair, and even those are unverified
against the document's own column headers. That is not a series. Publishing it would put a campaign-spend number
against a party whose report said something else.

## Why this is a disclosure finding

Wfpp art. 25 requires a financial report; it does not require a common template for expenditure. Each party's
accountant lays out the statement, and the ministry publishes what was filed. Income is comparable because the
register normalises it into one table. Expenditure is not normalised anywhere.

The Ctfpp says the same in its own words: its advice on the 2024 accounts asks BZK to "verduidelijking te geven
wat kwalificeert als gift in natura", to clarify the framework for neveninstellingen, and to give "een
geactualiseerde uitleg over subsidiabele en niet-subsidiabele uitgaven per categorie". A body that supervises
these reports is asking for the categories to be explained.

## What would close it

**Correction, 2026-11-20.** An earlier version of this section said the subsidieverantwoording is a "model
justification with fixed categories". The model exists — bijlage 2 of the Regeling financiering politieke
partijen, binding since 1 April 2025 and applicable from the 2024 reporting year — but its cost categories are
**not fixed**. The printed skeleton reads *Bestuurskosten / Bureaukosten / Verkiezingskosten / Etc.*, and the
binding part is the arithmetic: columns for the year and its comparator, a total of subsidiary spend, the granted
subsidy, and the difference. The row set is left to the party. Six parties sampled, six taxonomies. See
`docs/lanes/LANE-SUBSIDIEVERANTWOORDING.md` for the primary text and the page references.

So the routes are:

1. **A party-level series of three totals, not a category series.** Every sampled party prints a total of
   subsidiary spend and some subsidy figure, under four different labels. `party × year × {total subsidiable
   spend, subsidy, difference}` is defensible if each party's label-to-concept mapping and entity scope are
   recorded once. That is 19-20 PDFs a year, some 250 pages, and it yields totals only.
2. **A closed category list, if BZK adopts it.** The Ctfpp has asked for exactly that: "een geactualiseerde uitleg
   over subsidiabele en niet-subsidiabele uitgaven per categorie". Until it happens, the least-bad target is the
   nine activities already closed in Wfpp art. 7, which three of six sampled parties partly report by letter.
3. **Nothing.** Report the campaign lines as evidence, which is what this file does, and refuse the aggregate.

The refusal above stands: no spending series is published. What changes is only the reason it cannot be built
from the one document everyone assumed would allow it.

Until one of those happens, the page carries income and gifts and does not carry a spending series. An absent
number is honest; a wrong one is not.

## Receipts

- `out/spending-campaign.csv` — 131 lines, each with `amounts`, `n_amounts`, `quality` in
  {`pair`, `single`, `ambiguous`}, `value_eur` only where a pair exists, and the printed line as `raw_line`.
- `scripts/extract_spending.py` — the extractor, with the declared rule and its limits in the docstring.
- Conflicts: D66 2024, D66 2021, PvdD 2021, PvdD 2020, VVD 2023, SGP 2023, CU 2020, 50PLUS 2021, **NSC 2024**
  (€185.458 against €238.643) and **SGP 2024** (€7.500 against €814.541). An earlier version of this list gave
  eight of the ten; the two 2024 cases were found by an audit and are added here.
- The numbers are positional: `value_eur` is the amount in the second numeric column of the line, which is a
  **candidate** value for "actual" until the column heading has been checked against the party's own table.
