# GRADING — what a euro's grade means

A number in this repository is not a fact about money. It is a fact about a document. The grade says which
document, and how far the money can be followed from the treasury before the paper stops.

## The chain

Every euro is followed down six rungs, in this order, and the walk stops where the documents stop.

| rung | question | source of truth |
|---|---|---|
| r1 | which begroting chapter and beleidsartikel carries it | `budgettaire_tabellen`, fase `OWB` |
| r2 | the article's ceiling, and every amendment to it | `O1` (1e suppletoire), `O2` (2e suppletoire) |
| r3 | through which instrument: a subsidy scheme, a regeling, an opdracht, a bijdrage | `instrument_of_uitsplitsing_apparaat_naam` |
| r4 | which recipient, where recipients are published at all | `Financiele_instrumenten_*.csv` |
| r5 | the realisation | `budgettaire_tabellen`, fase `JV` |
| r6 | a Rekenkamer finding on that line | not yet probed |

## Status vocabulary

Used verbatim in `out/party-line-disclosure.csv` and in prose. Do not invent synonyms.

| status | meaning |
|---|---|
| `documented` | the rung exists in a source and carries a value |
| `documented-zero` | the rung exists and the value is 0; this is a finding, not a missing value |
| `named` | every euro at that rung is attributable to a named legal person |
| `partial` | some euros are named, the rest sit in an anonymised aggregate |
| `aggregate-only` | the rung exists only as `Geanonimiseerde ontvanger(s) van ... voor ...` |
| `absent` | the rung does not appear in the source for that year |
| `not-published` | the year lies outside the row-level register's coverage window (currently 2017-2024), so the rung cannot be read: not yet published, or withdrawn from the current vintage |
| `unavailable-in-source` | the source cannot serve the rung at all (r2: the API ignores `phase=O1/O2`) |
| `not-probed` | nobody has looked yet (r6 for now) |

`unavailable-in-source` and `not-probed` are deliberately excluded from `breaks`. They are gaps in the
instrument, not findings about disclosure. Everything else in `breaks` is a finding.

## Three numbers that never add up

The same appropriation line yields three different quantities, and adding them is the standard error this
repository exists to prevent:

- **ceiling** — `OWB`, what the begroting says may be spent;
- **realisation** — `JV`, what the jaarverslag says was spent;
- **named payment** — what the recipient register attributes to a named legal person.

`ceiling_k`, `realised_k`, `named_k` and `anon_k` are separate columns. `unreconciled_k` is
`realised_k - named_k - anon_k`: the part of the realisation the register does not distribute. It is a
measurement of disclosure, not a residual to be spread across recipients.

A `documented-zero` realisation against a non-zero ceiling is a reportable state. `Decentrale politieke
partijen` in 2025 is exactly that: 8.382k ceiling, 0 realised.

## Units

`bedrag_k` means EUR thousand everywhere in this store. The row-level register prints
`Bedrag (x1000)`; the chart API prints euros. Both are stored in EUR thousand, and the raw value and
multiplier are recoverable from the source file, which is never committed but always re-fetchable.

## Identity

`ontvanger_key` is `lower(trim(ontvanger))`, which mirrors the source's own convention (`id == titel.lower()`).
It is *not* identity. KvK is the only external identifier and it is blank for anonymised rows and for many
recent ones. Every merge that depends on a name is a decision and belongs in the `adjudication` table with
the field matched and the evidence:

- the payee is often not the party (`CDA` is paid as `Stichting Secretariaat CDA`, KvK 41152088);
- one entity can carry two identifiers across years (`SP` KvK 40346246 in 2020-2021, 12042006 in 2022-2024);
- one name can be anonymised one year and named the next (ProDemos, the Thorbecke chair).

## What is never done

- Never impute a recipient to close a gap.
- Never concatenate a series across a rename without showing the break.
- Never sum a ceiling into a payment total.
- Never quote a figure without its `fetch_id`, which resolves in `source_fetch` to url, retrieval timestamp,
  sha256 and licence.
