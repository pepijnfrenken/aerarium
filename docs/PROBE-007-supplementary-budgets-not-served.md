# Probe 007 — the supplementary budgets are advertised and not served

Rung 2 of the chain is "the article's ceiling, and every amendment to it: Voorjaarsnota, Najaarsnota,
suppletoire wetten". The chain has been reported as broken there since the first probe, on the grounds that the
open-data API does not serve the O1/O2 phases. That conclusion survives, but the reason given was wrong and the
evidence was thin. This probe settles it.

## What the API says it offers

`https://www.rijksfinancien.nl/swagger.json` (at the site root; `/open-data/swagger.json` returns an HTML page
with status 200, which is its own small trap). The budget endpoint
`/open-data/api/json/budgettaire_tabellen` declares:

- `phase` — string, **enum `["OWB", "O1", "O2", "JV"]`**
- `vuo` — string, **enum `["U", "O", "V"]`**
- `year`, `chapter`, `chapter_name`, `article`, `article_name`, `sub_article`, `minister`

So the supplementary phases are not merely undocumented; they are first-class values of a documented parameter.

## What it actually returns

Request: `?year=2024&chapter=XVI&vuo=U&phase=<value>`.

| phase asked for | rows returned | `fase` values inside the payload |
|---|---:|---|
| `OWB` | 219 | OWB 219 |
| `JV` | 237 | JV 237 |
| `O1` | 456 | **OWB 219, JV 237** |
| `O2` | 456 | **OWB 219, JV 237** |

The `O1` response is the **exact union** of the `OWB` and `JV` responses: 456 of 456 rows match on
`(index, bedrag)`, with nothing in one and absent from the other. The `O2` payload is byte-identical to `O1`
(same md5). **No row in either response carries `fase = O1` or `fase = O2`, in any chapter, in any year.**

That is worse than a 404. A 404 tells you the thing is not there. This returns a valid, plausible payload with a
success status, and a reader who asked for the first supplementary budget receives the draft and the annual
account instead, with no error and no warning.

## Why it matters for the chain

Every ceiling in this project is the **draft** ceiling, and the distance between it and the realised account
contains every Voorjaarsnota and Najaarsnota, which is precisely the movement rung 2 exists to record. The
project therefore reports no "budget versus actual" percentage: it would be a percentage against a ceiling that
was never the operative one.

## Where rung 2 could still be closed

Not from this API. The amendments are published as Kamerstukken — the suppletoire begrotingsstaten and their
memories van toelichting — one per ministry per amendment round, as PDF/HTML. Closing r2 means ingesting those
documents and keying each amendment to (year, chapter, article), which is a document-parsing job with no
machine-readable table behind it. That is a real ingest, and it is named here rather than approximated.

## One more thing this re-confirms

`beleid_of_niet_beleid` is the **empty string** in all 456 rows of the O1 response, straight from the source.
The column is empty upstream, not emptied by my loader. It does not split policy from apparatus spending, and no
figure in this project now depends on it.

## Query used

```
GET https://www.rijksfinancien.nl/open-data/api/json/budgettaire_tabellen
      ?year=2024&chapter=XVI&vuo=U&phase=O1
```

Note the parameter names: `phase`, not `fase`; `chapter`, not `hoofdstuk`. `fase` and `hoofdstuk` are the names
of the *output* fields, and passing them as filters is silently ignored — which is how an earlier probe
concluded "O1 returns nothing" when it had in fact asked for nothing in particular.
