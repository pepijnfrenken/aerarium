# Probe 006 — the recipient register is not a decomposition of the chapter total

**Result:** named recipients in the register sum to **€197.959.554k** against €493.337.650k of chapter totals for
2024 — 40,1%. But two chapters come out **above 100%**, which is impossible if the register were a breakdown of
the chapter's own money: **XVI VWS at 189,4%** and **XVII BHOS at 108,8%**.

A share above 100% is not a rounding problem. It means the two registers do not partition the same money, and
any flow percentage computed by dividing one chapter total by the other is arithmetic dressed as disclosure.

## What the overrun is

The four largest XVI rows are all `Zorginstituut Nederland` under `Bekostiging`:

- `BEK Bijdr Wlz` €15.550.000k
- `BEK Bijdrage Kosten Korting` €5.302.200k
- `BEK Rijksbijdrage 18-` €3.303.300k

That is **€24,4bn of `Bekostiging` against a chapter XVI expenditure total of €15,7bn**. The Wlz and the
Zorgverzekeringsfonds flow through the Zorginstituut and are financed largely by premiums, not by the
appropriation on chapter XVI. The register publishes the **recipient of the flow**; the chapter publishes the
**appropriation's share of it**. They are different quantities that share a budget structure.

XVII behaves the same way for a different reason: its recipient rows include ODA contributions that the
chapter total nets or books elsewhere, so the parts exceed the whole again.

## Why this decides the design

The join cannot be `chapter total → sum of recipients`. The register is published at the level of
**(hoofdstuk, artikel, instrument, regeling)**, and that is the level at which a recipient sum can be tested
against a budget line. Reconcile one instrument at a time and the parts can close; aggregate to the chapter and
the ZBO and statutory flows inflate it.

So the chain's r3→r4 edge is an instrument-level edge, and a chapter-level "how much reaches a named recipient"
figure is not computable from these two registers at all. The honest measure is per instrument-regeling:

- instrument budget (from `budget_line`, `fase='JV'`)
- named recipients (from `recipient_line`, `anonymised = false`)
- anonymised recipients (`anonymised = true`)
- residual = instrument budget − named − anonymised, which is money the register does not attribute

and a **grade per instrument**: does it reach a named recipient, only an anonymised one, or none at all.

## The disclosure regime is a break, not a trend

Recipient rows by year, and how much of the money is anonymised:

| year | rows | distinct recipients | anonymised rows | anonymised €k | named €k |
|---|---:|---:|---:|---:|---:|
| 2017 | 949 | 769 | 949 | 129.124.549 | 0 |
| 2018 | 974 | 806 | 974 | 140.807.305 | 0 |
| 2019 | 966 | 665 | 966 | 148.262.829 | 0 |
| 2020 | 82.653 | 66.841 | 891 | 157.113.968 | 18.684.059 |
| 2021 | 55.168 | 50.666 | 852 | 132.001.466 | 43.752.528 |
| 2022 | 30.249 | 18.541 | 1.041 | 49.953.605 | 108.942.770 |
| 2023 | 40.436 | 24.290 | 1.873 | 80.895.060 | 122.677.872 |
| 2024 | 66.269 | 46.619 | 944 | 4.740.918 | 197.969.404 |

Three regimes, not one series. 2017-2019 publish **only** anonymised recipients while carrying €129-148bn each.
2020-2023 publish both, with a few hundred anonymised rows still absorbing €50-157bn. 2024 collapses the
anonymised total to €4,7bn and names €198bn. The row counts also swing by two orders of magnitude, which is a
change in how detail is published, not in how much was paid.

Any multi-year flow series must show those three regimes as breaks. A line drawn through them would say
disclosure improved smoothly; it did not, it changed twice.

## What this rules out

- A single "share of the budget that reaches a named recipient" figure for the Rijk. Not computable.
- Chapter-level reconciliation. Fails on XVI and XVII by construction.
- Treating the 2024 naming rate as an improvement in transparency without noting that the anonymised rows did
  not disappear, they stopped being published at that level of aggregation.

## What it permits

An instrument-level grade per euro, which is the r3→r4 edge the chain was designed around, and a per-instrument
list of where the chain stops. That is the next build.
