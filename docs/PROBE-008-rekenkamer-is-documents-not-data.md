# Probe 008 — the Rekenkamer publishes findings as documents, not as data

Rung 6 of the chain is "a Rekenkamer finding on that line, where one exists". Before designing an ingest I
checked whether the Algemene Rekenkamer publishes anything machine-readable. It does not, on the evidence
below.

## What was probed

| URL | status | content | result |
|---|---:|---|---|
| `https://www.rekenkamer.nl/onderwerpen` | 200 | `text/html`, 259.257 bytes | topic index, no data files |
| `https://www.rekenkamer.nl/zoeken?q=politieke+partijen` | 200 | `text/html`, 202.027 bytes | search page, **zero** publication links in the HTML |
| `https://www.rekenkamer.nl/over-de-rekenkamer/open-data` | **404** | `text/html` | no open-data page exists |

On the search result page: no `href` to a publication, rapport or onderzoek path; no API, Solr or JSON endpoint
referenced in the markup; four mentions of `application/pdf` on the whole page. The page is a shell whose results
are fetched client-side, and no endpoint for that fetch appears in the returned HTML.

So there is no table to join. A Rekenkamer finding is a **PDF report with a title, a publication date and a
subject**, and attaching one to a budget line is a document-classification job, not a key join.

## What this means for rung 6

Rung 6 cannot be populated from a register, and it should not be faked with a keyword match. The shape it would
take, if it is built:

1. Enumerate the Rekenkamer's publications by crawling the topic and publication indexes (the site is
   JS-rendered, so this needs a browser, not `curl`).
2. Store each report's title, date, dossier and the chapters/articles it names — extracted from the PDF text, not
   guessed from the title.
3. Record, per report, the *matched* chapter with the sentence that justifies the match, and keep the unmatched
   ones as unmatched. A report about "the Ministry of Health" is not automatically a finding on article 3 of
   chapter XVI, and a project that grades every euro cannot afford a rung whose edges are title guesses.

Until that exists, every euro in the chain stops at rung 5, and the page says so. That is a statement about this
project's coverage, not about the Rekenkamer, which does publish the work — as documents.

## Why this is written down rather than left undone

Every other rung has a machine-readable source and a probe that says what it returns. Rung 6 has neither, and
"we did not get to it" is exactly the kind of silent gap that later reads as "there are no findings on this
line". There are findings; they are in a corpus that has not been read.

## Scope note

Building this is a widening beyond the budget and recipient registers: a document corpus, a crawler and a
classification step, with the same privacy and accusation discipline as the party corpus. It is named here so it
is a decision, not a drift.
