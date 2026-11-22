# FINDING 005 — the two ends: SP's millions are its own MPs, PVV's are nothing

Two parties, opposite ends of the same register. Both are correct filings. Neither means what a reader would assume.

## SP: €6.229.126,27 in "gifts", of which almost all is salary surrender

SP's gift total for 2022-2024 is the largest of any party apart from GroenLinks/PvdA. It is not outside money.

The 2024 report states it on one line:

    Totaal ontvangen bijdragen volksvertegenwoordigers 2024                          1.999.889
    Totale netto-afdracht volksvertegenwoordigers 2024 cf jaarrekening 2024 SP       1.999.889

Against €2.098.889,33 in gifts for 2024, that is **95,3% from SP's own elected representatives**. The mechanism is
the party's rule that a representative surrenders the parliamentary allowance and takes back a fixed salary; the
difference flows to the party and is filed as a contribution, because under the Wfpp that is what it is.

- 270 distinct SP "donors" across the three years on the **raw published name string**, median €20.579,22. On
  the page's lowercased-and-whitespace-normalised convention the same set is 269 keys and €20.634,90, because
  one spelling pair differs only in case. Both are stated because the count depends on which rule you name.
- Top 12 are all named representatives: S. Beckerman €155.887,70, M. van Nispen €147.665,33, P. Kwint
  €92.821,71, J. Dijk €89.222,37, M. Alkaya €87.754,32, and so on. Together they are 17,9% of the total. The
  register records no tenure, and these gifts span 2022-2024, so a 2024 seat cannot be asserted for a 2022 gift:
  the entries identify the donors, they do not establish that each was sitting in the year the money moved.
- Entity share of SP's money: **0,0%**. SP takes essentially nothing from companies or foundations.

So a chart of "private gifts per party" puts SP second, and that reading is wrong. SP is the party that funds
itself out of its own salaries. The page's income ratio is labelled "gift share, gross" for exactly this reason.

SP also reports its parliamentary group budgets separately: **Fractiebudget Tweede Kamer 2024 €2.508.000** and
**Eerste Kamer 2024 €135.434**. That is Kamer money for the group, distinct from the Wfpp subsidy the party
receives from BZK (€1.769.292 in 2024). Three flows, three names, and none of them is a gift from the public.

## PVV: no subsidy, two members, €150

PVV's reports for 2021-2024 all state the same three lines:

    Ontvangen subsidies:          €0
    Ontvangen bijdragen:          € 150 contributie
    Overige inkomsten:            €0

The 2024 report adds "Jaarlijks betalen de twee leden van de vereniging € 75 aan contributie", and a result of
**−€9.199** (2023: −€4.084). Its activities in 2024 "bestonden hoofdzakelijk uit het in stand houden van de
ledenadministratie".

**On the €12.803: the report contradicts itself and this file does not resolve it.** A summary line calls that
amount `Schulden`, but the balance sheet presents the same order of magnitude as negative equity, alongside
separate liability rows — €8.617 long-term and €4.500 in payable accountant costs. Until the two presentations
are reconciled, the honest statement is that PVV's 2024 filing shows a small negative position and small
liabilities, not a debt total of €12.803. Neither figure establishes how the party's wider political operation
is financed.

- PVV appears in **none** of the 19 subsidy rows for 2022-2024. Its own reports say €0 received, so this is not a
  hole in the register: the party takes nothing through the Wfpp subsidy route.
- Gifts: €35.000 (2022), €15.000 (2023), €0 (2024), all to Stichting Vrienden van de PVV, which is its only
  neveninstelling. No scientific bureau, no youth wing, nothing else named.
- 2025, to 8 October: **€1.000** from M. Vinogradovs to Stichting Vrienden van de PVV, flagged in the source as an
  anonymous gift above €250. Nothing in the final three weeks. Debts: nil.
- Seats: 17 (2021), 37 (2023), 26 (2025). Gifts per seat in 2025: **€38,46**.

## What this means for the chain

The Wfpp chain ends at the party. For SP it ends inside the party's own payroll. For PVV it ends almost
immediately, because there is nothing there to follow: a party with 37 seats reporting €150 of income means the
political operation is financed somewhere else.

That somewhere else is the parliamentary group, whose budget runs through the Tweede Kamer's own appropriation
(chapter II), not chapter VII. Following it would widen the scope beyond the Rijk party line, so it is recorded
here as the next widening candidate rather than assumed.

## Receipts

- `out/gifts_donors_public.csv`, partij = SP: 579 donor-total rows, 1.361 contribution rows.
- `corpus/text/2024_SP_1_626e6537.txt` lines 4346-4350 (volksvertegenwoordigers), 691-692 (fractiebudget).
- `corpus/text/2024_PVV_1_c36603f3.txt` lines 65-67 (income), 662 (two members), 450 (result).
- `out/gifts-2025-election.csv`, partij = 01. PVV, one row.
