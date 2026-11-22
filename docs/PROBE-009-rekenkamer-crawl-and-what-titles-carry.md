# Probe 009 — rung 6: the Rekenkamer register can be enumerated, and then it stops you

Vintage: 2026-11-22. Scripts `scripts/fetch_rekenkamer.py`, `scripts/classify_rekenkamer.py`. Artifact
`out/rekenkamer.json`. Corpus `corpus/rekenkamer/` (gitignored).

Rung 6 asks for a Rekenkamer finding on a line. `PROBE-008` established there is no machine-readable link
between a report and a begrotingsartikel, so the join has to be document classification. This probe is the
first attempt at the corpus that classification needs, and its result is partly a discovery about the sources
and partly a discovery about crawling.

## Enumeration works, and it is better than crawling HTML

`robots.txt` carries no `Disallow` and points at `sitemap.xml`. That file is a sitemap **index**: **55
sub-sitemaps** listing **5.260 distinct URLs**, of which **3.942** sit under `/documenten/`. Filtering to
non-video document pages from 2016 gives **2.677 pages** in scope.

That matters beyond convenience. Enumerating from the publisher's own index means coverage is what the
publisher declares, not what a crawler happened to reach. A link-following crawl cannot tell you what it
missed; a sitemap can.

Page URLs follow `/documenten/YYYY/MM/DD/slug`, and each page carries `pageTitle`, `publicationDate` and
`contentType` in an embedded JSON payload. Report pages are `pro:downloadDocument` and link their PDF under
`/site/binaries/site-content/collections/documents/...` — the same pattern as rijksoverheid.

## And then HTTP 403

**1.463 of the 2.677 pages** were harvested with metadata intact and **1.034** of those carry a PDF link. Then
the host began answering **403 in 27 ms** to everything, including `sitemap.xml`. **2.434 further requests**
were refused. **No PDF was downloaded**, so no text was extracted.

The cause was my rate: four concurrent connections at roughly seven requests a second, which is not a polite
way to read someone's publication register. The crawler now uses one connection at one request per second,
stops the pass on a 403 instead of retrying into it, and treats a failed row as not-done so the corpus cannot
silently become a sample of whatever happened to succeed. That last point was a real bug in the first version:
failures were recorded as done, which would have frozen a transient block into a permanent hole.

**The block persists.** Both user agents, both `sitemap.xml` and document pages, still 403 some hours later.
The remedy is to wait and resume, not to find a way around it.

## The alternative structured route does not answer

ARK reports sent to parliament are Kamerstukken, and the Officiële Publicaties collection has an SRU interface
that would carry dossier and ministry as structured fields — a far better join than keyword matching. It is at
`https://zoek.officielebekendmakingen.nl/sru/Search` with `x-connection=oep`, not on zoekservice (that host
serves cvdr, bwb and sc only, and answered `Unsupported parameter value` to every connection name I tried).

Every query form I sent to the OEP endpoint returned **HTTP 500**: bare keyword, `title=`, and
`dt.creator="Algemene Rekenkamer"`. The service is reachable and rejects the requests. Without its query
contract in hand I stopped rather than continue guessing at a public service, so this route is **untested, not
disproven**: if it works for anyone, it would replace the classification below with an identifier join.

## What the titles alone can carry, and what they cannot

With no PDF text, only the strong rule is available: a publication is attached to a chapter when **its own
title** names that ministry. Over the 1.463 publications:

| attachment | publications |
|---|---:|
| title names a chapter | 546 |
| of those, a Rekenkamer finding | 262 |
| no chapter named in the title | 917 |
| body text read | **0** |

The second row is the one that matters, and it came out of a review rather than out of the design. The register
carries the ministry's **reaction** to a finding, its answers to parliamentary questions about it, and covering
briefs, alongside the findings themselves. Attaching a ministry's own response to a budget line as though it
were an audit finding would invert the chain: the finding is the Rekenkamer's, the response is the auditee's.
Split by title form: 268 `overzicht fouten en onzekerheden`, 238 `reactie`, 134
`verantwoordingsonderzoek`, 91 `aandachtspunten`, 84 `beantwoording`, 21 `brief`, 627 `overig`.

By chapter, on title alone, the largest groups are VII Binnenlandse Zaken (79), IX Financiën (69), IV
Koninkrijksrelaties (65), X Defensie (55) and VI Justitie en Veiligheid (39).

**Body matches are null, not zero.** No document was read, so the body-match count is unmeasured. Recording it
as `0` would be a statement about documents nobody opened.

## The rule's precision, measured rather than assumed

Two terms in the chapter vocabulary are dangerous: `de koning` (a person's name, which appears in any report
mentioning the King) and `os` for BHOS. I sampled the attachments that look most likely to be wrong:

- **Chapter I (`de koning`), 13 matches, all correct**: they are the verantwoordingsonderzoeken for the King's
  budget, titled `Resultaten verantwoordingsonderzoek 2024 De Koning`.
- **Chapter H (BES-fonds), 29 matches, correct**: `Koninkrijksrelaties en BES-fonds` titles, which legitimately
  attach to both IV and H.
- **Chapter XVII, 27 matches, correct**: they name `Buitenlandse Handel en Ontwikkelingssamenwerking` in full.
- **1 attachment of 677 rests solely on a term of four characters or fewer**, and it is `acm` — the consumer
  authority's reaction to a report about heat networks, which is a real chapter XIII actor.

That is a sample, not a precision estimate. It says the obvious false positives are not there; it does not say
the rule is right 100% of the time, and the two counts are published apart so a reader can weigh the weak claims
separately.

## What rung 6 can and cannot claim today

A chapter-level attachment for 262 findings, from titles, over 55% of the publication register, with no text
read. That is **not** a finding on a budget line: a report naming a ministry does not name article 3 of that
ministry's chapter, and this project does not attach to an article it cannot identify. Rung 6 therefore stays
open, and every euro still stops at rung 5 until the corpus is complete and the text is read.

The next step is mechanical: resume the fetch at one request per second when the block lifts, download the
**1.034** PDFs already enumerated, extract text with `pdftotext`, and let the body rule run — then publish the
body-match count beside the title-match count and state the gap between them.
