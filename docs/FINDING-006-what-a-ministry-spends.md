# Finding 006 — How big is a ministry, and what is it spending?

**Correction, 2026-11-21.** The first version of this finding reported a gross chapter sum of €493.337.650k and
programme spending of €336.200.500k. Both were wrong, and the cause was a column I never filtered on.
`budget_line` carries a `vuo` axis with three values: **`O` = ontvangsten (receipts)**, **`U` = uitgaven
(expenditure)**, **`V` = verplichtingen (commitments)**. I summed all three. That inflated 2016 to €698bn, about
double what the Dutch state spends, and I published the 2024 total without checking it against a neighbouring
year. The check that caught it was an eleven-year series in `scripts/flow.py`: the drop from €899bn (2019) to
€338bn (2020) was not a budget cut, it was my query.

**Corrected answer, 2024, realised account, expenditure axis only:** **€401.303.575k**. Of that,
**€59.267.080k** is financial transactions and **€10.566.821k** moves to another budget chapter.
**Programme spending is €331.469.674k.** Personnel is **€17.503.748k, or 5,3%** of it — and that is not the
state's wage bill, for the reason in section 4.

Artifact: `out/govrun.json`, built by `scripts/govrun.py`. Bound in `scripts/verify_bindings.py`.

## 1. The three axes

| axis | `vuo` | 2024 (€k) | what it is |
|---|---|---:|---|
| receipts | `O` | 92.034.075 | money coming in, including fund revenues and fines |
| **expenditure** | `U` | **401.303.575** | what the chapters spend |
| commitments | `V` | 0 | verplichtingen; absent 2023-2025, present 2016-2022 |

Commitments are not a smaller version of expenditure and were never additive to it. Where both exist they
differ in timing, not in kind. Adding them is the error this finding used to make.

## 2. Within the expenditure axis

| category | amount (€k) | share of axis | what it is |
|---|---:|---:|---|
| programme spending | 331.469.674 | 82,6% | money leaving for people, goods, subsidies and transfers |
| financial transactions | 59.267.080 | 14,8% | `Leningen` 57.490.007; `Mutaties in rekening-courant en deposito's`; `Vermogensverschaffing/-onttrekking`; `Storting/onttrekking begrotingsreserve` |
| inter-chapter transfers | 10.566.821 | 2,6% | `Bijdrage aan (andere) begroting(shoofdstukken)` — one chapter paying another |

The classification of every instrument is printed inside the artifact, so a reader who disagrees can recompute.

Two rows show why the axis matters. **Financiën** appears in the chapter table at €76.312.346k and is a
**€21.725.430k** ministry with **€54.586.916k** of loans and treasury movements beside it. **IenW** appears at
€13.918.645k and is **€3.510.189k** of spending plus a **€10.408.456k** transfer to the funds.

## 3. Each chapter on programme spending, 2024 (€k)

| ch | ministry | programme | not programme | personnel | personnel % |
|---|---|---:|---:|---:|---:|
| XV | Sociale Zaken en Werkgelegenheid | 110.211.151 | 59.366 | 511.117 | 0,5% |
| VIII | Onderwijs, Cultuur en Wetenschap | 53.448.818 | 3.014.965 | 365.321 | 0,7% |
| B | Gemeentefonds | 43.835.927 | 0 | 0 | — |
| VI | Justitie en Veiligheid | 25.483.438 | 0 | 1.447.008 | 5,7% |
| IX | Financiën en Nationale Schuld | 21.725.430 | 54.586.916 | 4.521.103 | 20,8% |
| XVI | Volksgezondheid, Welzijn en Sport | 15.729.481 | 21.438 | 509.869 | 3,2% |
| X | Defensie | 12.358.734 | 89.477 | 8.308.166 | 67,2% |
| VII | Binnenlandse Zaken en Koninkrijksrelaties | 10.762.328 | 162.943 | 466.542 | 4,3% |
| V | Buitenlandse Zaken | 10.187.379 | 0 | 0 | — |
| XIII | Economische Zaken | 8.775.808 | 1.233.862 | 551.702 | 6,3% |
| C | Provinciefonds | 3.954.345 | 0 | 0 | — |
| XVII | Buitenlandse Handel en Ontwikkelingssamenwerking | 3.945.006 | 40.800 | 0 | — |
| XIV | Landbouw, Natuur en Voedselkwaliteit | 3.937.436 | 106.519 | 196.179 | 5,0% |
| XII | Infrastructuur en Waterstaat | 3.510.189 | 10.408.456 | 602.353 | 17,2% |
| A | Infrastructuurfonds | 3.397.282 | 0 | 0 | — |
| H | BES-fonds | 103.883 | 0 | 0 | — |
| IV | Koninkrijksrelaties | 103.039 | 109.159 | 24.388 | 23,7% |

Four chapters are funds rather than ministries (B Gemeentefonds, C Provinciefonds, A Infrastructuurfonds, H
BES-fonds): money passing through to municipalities, provinces and the Caribbean Netherlands. They are listed
because they are chapters of the Rijksbegroting, not because they are organisations.

## 4. Personnel: why 5,3% is not the wage bill

`Personele uitgaven` is an instrument line, and ministries do not use it uniformly.

- **Defensie** books €8.308.166k there — 67,2% of its programme spending. A defence force whose cost is mostly
  people is plausible.
- **Buitenlandse Zaken** (V) and **BHOS** (XVII) show **zero** in 2024 while their other-year personnel totals
  are not zero. Their staff costs are booked as contributions or opdrachten.
- Six chapters — B, V, XVII, C, A, H — have no personnel row at all in 2024.

A national share over this instrument measures **which ministries use the label**, not how much of the Dutch
state's money goes on pay. The per-chapter column is what the account says; the national 5,3% carries that
warning in the artifact. Answering the wage-bill question properly needs the apparaatskosten tables, or the
Jaarrapportage Bedrijfsvoering Rijk — a separate ingest, named rather than approximated.

## 5. Draft against realisation

The API serves `OWB` (draft) and `JV` (realised) and **not O1/O2**, the suppletoire wetten. "Ceiling" here
means the draft ceiling, and the distance to the account contains every Voorjaarsnota and Najaarsnota this
source cannot show. No budget-versus-actual percentage is published for that reason.

## 6. Two more columns that do not do what their names suggest

**`beleid_of_niet_beleid` is blank in all 51.146 rows of every year 2016-2026** — measured across the whole
table, not just the expenditure axis, and printed under `column_integrity`. It does not split policy from
apparatus spending. I claimed it did, from the column's presence alone.

**`index_id` is a hierarchy node, not a row key.** Up to six rows share one index carrying different amounts —
separate price-level adjustments, not repeats. Dedupe is on the full row tuple at read time; 94 exact duplicates
exist and are removed in the query rather than by rebuilding a table other steps read.

## 7. Coverage

Twenty-three chapter identifiers, eleven years. Structural, named, not failures:

- XVIII (Wonen en Rijksdienst) ends 2018; XIV (LNV) begins 2019 — the ministry was merged and recreated.
- XX (Asiel en Migratie) exists from 2025; H (BES-fonds) from 2020; XIX (Nationaal Groeifonds) only 2021-2022.
- I (De Koning) has no rows for 2021-2024; III (Algemene Zaken) none for 2021.
- II and XI serve no rows in any year.

A series across those boundaries reconciles a renamed ministry or shows the break. It does not silently
continue.
