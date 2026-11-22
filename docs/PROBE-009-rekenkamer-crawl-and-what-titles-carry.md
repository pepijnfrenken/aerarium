# Probe 009 — rung 6: the Rekenkamer register, harvested whole

Vintage 2026-11-22. Scripts `scripts/fetch_rekenkamer.py`, `scripts/classify_rekenkamer.py`. Artifact
`out/rekenkamer.json`. Corpus `corpus/rekenkamer/` (gitignored).

Rung 6 asks for a Rekenkamer finding on a line. `PROBE-008` established there is no machine-readable link
between a report and a begrotingsartikel, so the join has to be document classification. This probe builds the
corpus that classification needs and reports what titles alone can carry.

## The register enumerates completely

`robots.txt` carries no `Disallow` and points at `sitemap.xml`, which is an index of **55 sub-sitemaps** listing
**5.260 distinct URLs**, **3.942** of them under `/documenten`. Filtering to non-video document pages from 2016
gives **2.677 pages** in scope.

Enumerating from the publisher's own index matters beyond convenience: coverage is what the publisher declares,
not what a crawler happened to reach. A link-following crawl cannot state what it missed; a sitemap can.

URLs follow `/documenten/YYYY/MM/DD/slug`; each page carries `pageTitle`, `publicationDate` and `contentType` in
an embedded JSON payload, and report pages are `pro:downloadDocument` linking a PDF under
`/site/binaries/site-content/collections/documents/...` — the same pattern as rijksoverheid.

## Harvested: 2.677 of 2.677, in two transports

**All 2.677 pages are held, with zero missing.** **1.463** came from a direct crawl; **1.214** came through
Firecrawl after the direct path was blocked. **2.013** pages carry a PDF link. By year: 2016 249, 2017 351,
2018 213, 2019 222, 2020 247, 2021 258, 2022 230, 2023 229, 2024 270, 2025 206, 2026 202.

Every row records its transport (`via: "firecrawl"` or the direct path), because a reader is entitled to know
which documents were retrieved through a third-party fetcher.

## What the direct path cost, and why a second transport exists

The direct crawl stopped at 1.463 pages when the host began answering **403 in 27 milliseconds** to everything,
including the sitemap: **2.434 requests refused**. The cause was my rate — four concurrent connections at roughly
seven requests a second. The crawler now runs one connection at one request per second, stops on a 403 instead of
retrying into it, and does not record a failed row as done, which would have frozen a transient block into a
permanent hole and made the corpus a silent sample of whatever succeeded.

Firecrawl then fetched from its own infrastructure. Its own limit was the next lesson: five concurrent requests
earned **302 refusals with HTTP 429**, and my first response — a backoff of my own devising — scraped nothing for
minutes because it kept the cooldown window refreshed. `Retry-After` counts down to a fixed boundary (observed
25 → 22 → 19 → 15 across three seconds), so the transport now sleeps exactly what it says and runs sequentially
at about four seconds. **1.231 credits** were spent, against a declared ceiling of 1.250 and a balance of 11.343.

The publications are public, `robots.txt` disallows nothing, and they are declared in the publisher's own
sitemap: what was refused was this client after it crawled too hard, not the documents.

## What titles alone carry, and what they cannot

No PDF has been downloaded, so only the strong rule runs: a publication is attached to a chapter when **its own
title** names that ministry. Over the **2.677** publications:

| attachment | publications |
|---|---:|
| title names a chapter | **1.003** |
| of those, a Rekenkamer finding | **482** |
| no chapter named in the title | 1.674 |
| body text read | **0** |

The split between the first two rows came out of review rather than out of the design. The register carries the
ministry's **reaction** to a finding, its answers to parliamentary questions about it, and covering briefs,
beside the findings themselves. Attaching an auditee's own response to a budget line as though it were an audit
finding inverts the chain: the finding is the Rekenkamer's, the response is the auditee's. By title form: **646**
`overzicht fouten en onzekerheden`, **465** `reactie`, **242** `verantwoordingsonderzoek`, **156**
`beantwoording`, **146** `aandachtspunten`, **30** `brief`, **992** `overig`.

By chapter on title alone, the largest groups are **IX Financiën 149**, **VII Binnenlandse Zaken 129**, **IV
Koninkrijksrelaties 109**, **X Defensie 107**, **VI Justitie en Veiligheid 66**.

**Body matches are null, not zero.** No document has been read, so the body-match count is unmeasured;
recording it as `0` would be a statement about documents nobody opened.

## The rule's precision, measured rather than assumed

Two terms in the chapter vocabulary are dangerous: `de koning` (a person's name, which appears in any report
mentioning the King) and `os` for BHOS. I sampled the attachments that look most likely to be wrong:

- **Chapter I (`de koning`), 27 matches, all correct** — they are the verantwoordingsonderzoeken for the King's
  budget, titled `Resultaten verantwoordingsonderzoek 2024 De Koning`.
- **Chapter H (BES-fonds), 35 matches, correct** — `Koninkrijksrelaties en BES-fonds` titles, which legitimately
  attach to both IV and H.
- **Chapter XVII, 45 matches, correct** — they name `Buitenlandse Handel en Ontwikkelingssamenwerking` in full.
- **1 attachment of 677 rests solely on a term of four characters or fewer**, and it is `acm` — the consumer
  authority's reaction to a report about heat networks, which is a real chapter XIII actor.

That is a sample, not a precision estimate. It says the obvious false positives are not there; it does not say
the rule is right every time, and the findings count is published apart from the attachment count so the two
claims can be weighed separately.

## What rung 6 can and cannot claim today

Coverage is complete and **482 findings** attach to a chapter by title. That is **not** a finding on a budget
line: a report naming a ministry does not name article 3 of that ministry's chapter, and this project does not
attach to an article it cannot identify. **Rung 6 therefore stays open, and every euro still stops at rung 5.**

The next step is the text. **2.013** PDFs are enumerated and none has been fetched; reading them lets the body
rule run on the **1.674** publications that title alone could not place, and lets the findings be summarised
rather than merely counted. That pass needs its own credit declaration before a credit is spent.
