# PROBE 001 — what the sources actually return

Retrieved 2026-11-20, before any ingester exists. Every figure below comes from a real call or a real file,
with the URL in `data/raw/probe-2026-11-20/`. Licence on all rijksfinancien open data is CC-0 / publiek domein
(Ministerie van Financiën, dataset metadata dated 21-05-2025).

## 0. Correction first, because it changes the design

My first reading was that the recipient register and the budget tables have no shared key. That was wrong, and
the mistake is instructive: I probed the **chart API** (`/open-data/api/json/v2/financiele_instrumenten/*`),
which returns four flat aggregate lists — `hoofdstukken`, `artikelen`, `regelingen`, `ontvangers` — each keyed
only by `id` (= `titel` lowercased), with no edge between scheme and recipient. Concluding "no join exists"
from that would have been a finding about my probe, not about disclosure.

The row-level data is published as a **bulk download**, and it carries the edge, the amount, the legal form and
the KvK number:

```
https://www.rijksfinancien.nl/sites/default/files/bestanden/open_data/Financiele_instrumenten_2017-2024.csv
277,664 data rows · 70.5 MB · semicolon-delimited · CRLF · UTF-8 BOM
Begrotingsjaar;Begrotingshoofdstuk;Begrotingsnaam;RIS/IBOS-nummer;Artikel;Artikelonderdeel;
Instrument;Detail;Regeling;Ontvanger;Bedrag (x1000);KVKnummer;Rechtsvorm;Plaats
```

The dataset description states the publication cadence: recipients are published **once a year, with the
slotwet, on verantwoordingsdag**, as enrichment on top of the begroting, and "de lijsten zijn deels
geanonimiseerd" under the AVG.

## 1. The budget spine — `/open-data/api/json/budgettaire_tabellen`

OpenAPI 3.1.0, "Rijksfinancien: Open API" 1.0.0, schema at `/swagger.json` (in this folder).

- Required: `year` (integer), `phase` ∈ `OWB` (begroting), `O1` (1e suppletoire), `O2` (2e suppletoire),
  `JV` (jaarverslag).
- Optional: `vuo` ∈ U/O/V, `chapter`, `chapter_name`, `article`, `article_name`, `sub_article`, `minister`.
- One row = one appropriation line, with its whole path in named fields:

```
index                            VII.1.2.1.666806.U
jaar, fase, vuo, bedrag
hoofdstuk_nummer / hoofdstuk_naam        VII  Binnenlandse Zaken en Koninkrijksrelaties
artikel_nummer / artikel_naam            1    Openbaar bestuur en democratie
artikelonderdeel_nummer / _naam          2    Democratie
instrument_of_uitsplitsing_apparaat_…    1    Subsidies (regelingen)
regeling_detailniveau_naam / _nummer     Politieke partijen  666806
```

`bedrag` reads as € thousand (see §3 for the check). Chapter VII 2026 returns 358 rows in one call, so the
whole Rijk is a few thousand rows per year-phase: the spine is cheap.

## 2. The party line, rung by rung

Chapter VII, artikel 1, artikelonderdeel 2 (Democratie), instrument Subsidies (regelingen), all € thousand:

| regeling | 2025 OWB (ceiling) | 2025 JV (realisation) | 2026 OWB |
|---|---|---|---|
| Politieke partijen | 32.910 | 26.929 | 32.232 |
| Decentrale politieke partijen | 8.382 | **0** | 8.150 |
| Toerusting en ondersteuning politieke ambtsdragers | — | — | 3.001 + 540 (opdrachten) + 7.818 (inkomensoverdr.) |

"Decentrale politieke partijen" is a ceiling of €8,4M with a realised €0 in the jaarverslag line. A ceiling is
not a payment, and here the gap is the whole line.

**`index` is not stable across phases.** Same regeling, same instrument, same article:

- 2025 OWB `VII.1.2.1.595675.U`
- 2025 JV  `VII.1.2.1.685653.U`

Join begroting → jaarverslag on the *path*, never on `index`.

## 3. What the recipient file says about the same regeling

Rows where `Regeling = "Politieke partijen"`, summed from `Bedrag (x1000)`:

| year | rows | total €k | named rows | named €k | anonymised rows | anonymised €k |
|---|---|---|---|---|---|---|
| 2017 | 0 | — | 0 | — | 0 | — |
| 2018 | 0 | — | 0 | — | 0 | — |
| 2019 | 1 | 17.452 | 0 | 0 | 1 | 17.452 |
| 2020 | 12 | 23.777 | 12 | 23.777 | 0 | 0 |
| 2021 | 16 | 27.647 | 15 | 27.011 | 1 | 636 |
| 2022 | 6 | 27.449 | 5 | 5.340 | 1 | 22.109 |
| 2023 | 5 | 29.458 | 4 | 5.137 | 1 | 24.321 |
| 2024 | 20 | 4.510 | 20 | 4.510 | 0 | 0 |

The same scheme, the same ministry, published at four different granularities in six years:

- **2019** — fully anonymised: `Geanonimiseerde ontvanger(s) van Subsidies (regelingen) voor Politieke partijen`.
- **2020** — fully named, with KvK numbers, full amount (12 recipients).
- **2021** — 15 named recipients (€27,0M) plus one small anonymised row (€0,6M). Mostly named, not fully.
- **2022, 2023** — a small named remainder (€5,1–5,3M) plus one anonymised row carrying the bulk (€22,1M, €24,3M).
- **2024** — 20 named recipients totalling €4,5M and no anonymised row at all. The remainder is not published
  in any form. The 2024 slice also carries party amounts that cannot be the subsidy (VVD €5k, D66 €4k, CDA
  €3k against a €32,9M ceiling in the following year's begroting), so part of it is residual payment, not
  subsidy. **2024 is unverified until reconciled against the 2024 slotwet.** Do not report the 2024 figure as
  a subsidy total.

Check on units: `Ontvanger = Zorginstituut Nederland, 2025 = 41.063.185.000` in the API is €41,1bn, i.e. euros;
the bulk file column is labelled `Bedrag (x1000)`. Two units in one data family. Normalise on ingest, carry the
raw value and the multiplier.

The payee is not always the party. The CDA is absent from the 2020 file; in 2021 its subsidy arrives under
`STICHTING SECRETARIAAT CDA` (KvK 41152088). D66 receives as `D66` (KvK 40407863), the SP as `SP`
(KvK 40346246 in 2020-2021, **12042006** in 2022-2024, legal form "Besloten Ven…" in 2024). Identity is the
difficulty, exactly as the naming doc predicted, and the KvK field both solves and complicates it.

## 4. The neveninstellingen are structurally absent from the register

Searched all 277,664 rows for the party scientific institutes: `telders` 0 rows, `wiardi` 0 rows,
`mierlo` 0 rows that are the Mr. Hans van Mierlo Stichting, `bolkestein` 0 rows. They receive no published
Rijks subsidy under any instrument in 2017-2024.

That is not an accident of data quality. It follows from the statute (§5): the party receives the subsidy, and
the transfer from the party to its own neveninstelling is exempt from registration at both ends.

What does appear in the party-adjacent zone, named, with KvK:

| entity | regeling | years and €k |
|---|---|---|
| Stichting Kennispunt Lokale Politieke Partijen (KvK 81607393) | Toerusting en ondersteuning politieke ambtsdragers; Weerbaar bestuur | 2021 15; 2022 330; 2023 354+13; 2024 360; 2025 448 (API) |
| Stichting ProDemos (KvK 50938053) | ProDemos; Toerusting…; Verbinding inwoner en overheid | anonymised 2017-2019, named from 2020 |
| Stichting Professor mr. J.R. Thorbecke Leerstoel (KvK 41167405) | Stichting Thorbeckeleerstoel | anonymised 2019 (€165k), named 2021 (€99k), 2024 (€376k) |

ProDemos and the Thorbecke chair show the same publication drift as the parties: the same entity anonymised in
one year and named with a KvK number in the next. Anonymisation is a per-year publication practice, not a
property of the entity.

## 5. The statutory closed set for neveninstellingen

Wfpp (BWBR0033004, geldend 06-06-2026):

- **art. 1(f)** — neveninstelling = a politiek-wetenschappelijk instituut (art. 2), a politieke
  jongerenorganisatie (art. 3), an instelling voor buitenlandse activiteiten (art. 4), or a rechtspersoon
  designated under art. 5.
- **art. 2-4** — at most **one** of each per party; designated by the party, written consent by the institute,
  notified in writing to the minister of BZK.
- **art. 5(3)** — if a party fails to designate a qualifying rechtspersoon, **the minister designates it**.
- **art. 21(2)(b)** — a party need not register contributions **from its own neveninstellingen**.
- **art. 30(3)** — a nevenstelling need not register contributions **from its own party**.

Those last two close the loop: money moving inside a party group is legally invisible on both sides. Art. 30
does require each neveninstelling to publish contributions of €1.000 or more per gever per year, with an
accountant's statement, and the minister publishes those overzichten. Third-party money into a neveninstelling
is therefore visible; party money into its own neveninstelling is not.

The designation list is public: the Dashboard partijfinanciering (launched 20-05-2026, per the BZK press
release of that date) states it contains "een overzicht van neveninstellingen" and "de hoogte van subsidies".

## 6. Defects that would corrupt a naive ingester

1. **`year` is ignored on the `ontvangers` search endpoint.** `year=2025` and no-year returned the identical 17
   rows spanning 2017-2025, and the response echoes `jaar: null`. Paginate the full set (`start`/`limit`) and
   filter client-side. Trusting the parameter double-counts across years.
2. **`index` changes between phases** (§2). Join on the path.
3. **`Regeling` names drift, truncate and carry typos across years**: `Toer. onderst. Pol A` (2020) →
   `Toerusting en ondersteuning politieke ambtsdragers` (2021+) → `Toerusting en ondersteuning politieke am`
   (2024); `Verb. inw. en overh.` → `Verbinding inwoner en overheid` → `Verbinding inwoner en oerheid` (2023,
   typo). The regeling name is not a key. Reconcile on (hoofdstuk, artikel, artikelonderdeel, instrument) plus
   a curated name table, and show the break where a series renames.
4. **`id = titel.lower()` exactly**, every row tested. No RSIN, no normalisation beyond case. KvK is the only
   external identifier and it is **blank for 13 of 20** named party rows in 2024 and blank for all anonymised
   rows.
5. **One entity, two KvK numbers**: SP 40346246 (2020-2021) vs 12042006 (2022-2024). Do not coalesce
   silently; adjudicate and record the decision.
6. **8.241 `regelingen`, 941 `artikelen`, 176 `hoofdstukken`** in the aggregate endpoints vs 277.664 row-level
   records. The aggregate lists are chart inputs, not a rollup you can validate against: `hoofdstukken` totals
   are sums over all years, and an entity can appear in several chapters.

## 7. Not yet probed

- `partijfinanciering.nl` — the neveninstellingen overview and the subsidy table (form, keys, download or scrape).
- Wfpp filings per neveninstelling (art. 30 overzichten) — the third-party money side.
- Kamerstukken / SRU (`zoek.officielebekendmakingen.nl`) — the bewijsmiddel for doelstelling and amendment text.
- Rekenkamer findings mapped to article numbers.
- Whether the v1 `financiele_instrumenten/instruments` endpoint still exists (it 404s).
- 2025 and later recipients: the bulk file stops at 2024; the API carries 2025 rows, so the file lags a year.
