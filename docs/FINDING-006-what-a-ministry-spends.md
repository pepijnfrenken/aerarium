# Finding 006 — How big is a ministry, and what is it spending?

**Answer, 2024, realised account:** the seventeen budget chapters add to **€493.337.650k**. That is not what
the state spent. **€157.137.150k of it — 31,8% — is not expenditure at all**: receipts, money moved from one
chapter to another, and loans. What remains is **€336.200.500k**. Of that, the line the register labels
personnel is **€17.511.565k, or 5,2%** — and that number cannot be read as the state's wage bill, for the reason
given in section 4.

Artifact: `out/govrun.json`, built by `scripts/govrun.py`. Every figure below is bound in
`scripts/verify_bindings.py` and fails the build if it drifts.

## 1. The correction that makes the rest readable

My first pass summed the chapters and reported "€493bn". An audit-adjacent check on the largest single
instrument per chapter found chapter XII at **+364,8%** against its own draft budget, which is not a plausible
year. It was one line: article 26, instrument `Bijdrage aan (andere) begroting(shoofdstukken)`, €10.408.456k,
present in the realised account and absent from the draft because in the draft that money is booked in the fund
it goes to.

That line is not spending. It is one chapter paying another. Adding chapters that contain such a line counts
the same euro twice, and no table in this source warns you.

The same inspection turned up two more categories sitting inside the total:

| category | amount (€k) | share of gross | what it is |
|---|---:|---:|---|
| expenditure | 336.200.500 | 68,2% | money leaving for people, goods, subsidies and transfers |
| financial transactions | 133.083.833 | 27,0% | `Leningen` 105.978.326; `Mutaties in rekening-courant en deposito's` 22.314.364; `Vermogensverschaffing/-onttrekking` 3.672.958; `Storting/onttrekking begrotingsreserve` 1.118.185 |
| receipts | 13.486.496 | 2,7% | `Ontvangsten` 11.252.365 and `Diverse ontvangsten EU` 2.234.131 — money coming **in** |
| inter-chapter transfers | 10.566.821 | 2,1% | `Bijdrage aan (andere) begroting(shoofdstukken)` |

The classification is a judgement and is printed inside the artifact with every instrument behind it, so a
reader who disagrees can recompute. The receipt case is not a judgement at all: a line named `Ontvangsten`
inside an expenditure total is a category error, and it appears in seven chapters, the largest being EZK at
€6.766.483k.

## 2. What each ministry is, on expenditure

2024, realised, expenditure only (€k). The last column is personnel as a share of that ministry's expenditure.

| ch | ministry | expenditure | not expenditure | personnel | personnel % |
|---|---|---:|---:|---:|---:|
| XV | Sociale Zaken en Werkgelegenheid | 110.211.151 | 2.840.963 | 511.117 | 0,5% |
| VIII | Onderwijs, Cultuur en Wetenschap | 55.196.631 | 3.016.862 | 365.321 | 0,7% |
| B | Gemeentefonds | 43.835.927 | 0 | 0 | — |
| VI | Justitie en Veiligheid | 25.641.414 | 1.350.469 | 1.454.325 | 5,7% |
| IX | Financiën en Nationale Schuld | 24.549.967 | 128.479.974 | 4.521.103 | 18,4% |
| XVI | Volksgezondheid, Welzijn en Sport | 15.729.481 | 66.003 | 509.869 | 3,2% |
| X | Defensie | 12.358.734 | 89.477 | 8.308.166 | 67,2% |
| VII | Binnenlandse Zaken en Koninkrijksrelaties | 10.762.328 | 162.943 | 466.542 | 4,3% |
| V | Buitenlandse Zaken | 10.187.379 | 2.234.131 | 0 | — |
| XIII | Economische Zaken | 8.775.808 | 8.000.345 | 551.702 | 6,3% |
| C | Provinciefonds | 3.954.345 | 0 | 0 | — |
| XVII | Buitenlandse Handel en Ontwikkelingssamenwerking | 3.945.006 | 40.800 | 0 | — |
| XIV | Landbouw, Natuur en Voedselkwaliteit | 3.937.436 | 337.568 | 196.179 | 5,0% |
| XII | Infrastructuur en Waterstaat | 3.510.689 | 10.408.456 | 602.853 | 17,2% |
| A | Infrastructuurfonds | 3.397.282 | 0 | 0 | — |
| H | BES-fonds | 103.883 | 0 | 0 | — |
| IV | Koninkrijksrelaties | 103.039 | 109.159 | 24.388 | 23,7% |

Two rows show why the naive table was wrong. **Financiën** looks like a €153bn ministry and is a
**€24,5bn** ministry with **€128,5bn of loans and treasury movements** beside it. **IenW** looks like a
**€13,9bn** ministry and is a **€3,5bn** ministry plus a **€10,4bn** transfer to the funds.

Three chapters are funds rather than ministries (B Gemeentefonds, C Provinciefonds, A Infrastructuurfonds, H
BES-fonds): money that passes through to municipalities, provinces and the Caribbean Netherlands. They are
listed because they are chapters of the Rijksbegroting, not because they are organisations.

## 3. Draft against realisation

The API serves `OWB` (draft) and `JV` (realised) and **not O1/O2**, the suppletoire wetten. So the ceiling
here is the *draft* ceiling, and the distance between it and the account contains every Voorjaarsnota and
Najaarsnota this source cannot show. That is why this finding reports the split by instrument and not a
"budget versus actual" percentage: the percentage would be a statement about a ceiling the source never
published.

## 4. Personnel: why 5,2% is not the wage bill

`Personele uitgaven` is an instrument line, and ministries do not use it uniformly.

- **Defensie** books €8.308.166k there — 67,2% of its expenditure. That is a defence force whose cost is
  mostly people, which is plausible.
- **Buitenlandse Zaken** (V) and **BHOS** (XVII) show **zero** in the same year, while their eleven-year
  personnel totals are not zero. Their staff costs are booked elsewhere, as contributions or opdrachten.
- Six chapters — B, V, XVII, C, A, H — have no personnel row at all in 2024.

A national share computed over this instrument therefore measures **which ministries use the label**, not how
much of the Dutch state's money goes on pay. The per-chapter column is reported because it is what the account
says; the national 5,2% carries that warning in the artifact.

Answering the wage-bill question properly needs the apparaatskosten tables (personeel + materieel per
ministry) from the begroting's own apparatus section, or the Jaarrapportage Bedrijfsvoering Rijk. That is a
different source and a separate ingest. It is named here rather than approximated.

## 5. Two columns that do not do what their names suggest

**`beleid_of_niet_beleid` is blank in all 51.146 rows of every year 2016-2026.** It does not split policy from
apparatus spending. I stated that it did, out loud, on the strength of the column existing; the count that
disproves it is printed in the artifact under `column_integrity`.

**`index_id` is a hierarchy node, not a row key.** Six rows under one index carry different amounts for the
same instrument — separate price-level adjustments, not repeats. Deduplicating on the id would delete real
budget lines. The store is deduplicated on the full row tuple instead, at read time: 94 exact duplicate rows
were created by repeated loads and are removed in the query rather than by rebuilding a table that other steps
are reading.

## 6. Coverage

Twenty-three chapter identifiers, eleven years. The gaps are structural and named, not failures:

- XVIII (Wonen en Rijksdienst) ends in 2018; XIV (LNV) begins in 2019 — the ministry was merged and recreated.
- XX (Asiel en Migratie) exists only from 2025.
- H (BES-fonds) from 2020; XIX (Nationaal Groeifonds) only 2021-2022.
- I (De Koning) has no rows for 2021-2024; III (Algemene Zaken) none for 2021.
- II and XI serve no rows in any year.

A series across those boundaries reconciles a renamed ministry or it shows the break. It does not silently
continue.
