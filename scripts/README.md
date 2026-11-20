# scripts

Three generators, in the order they run. All write into `out/`; none writes to `data/`.

## 1. `extract_gifts.py` — donor-level gifts from the dashboard

Reads nothing. Fetches `/dashboard/jaarlijkse-verantwoording/giften/{jaar}/{partij}` for 2022-2024 and
extracts the `giften_totaal` objects from the Next.js RSC payload. The rendered table body is empty; the rows
are in the payload, so no browser is needed.

    .venv/bin/python scripts/extract_gifts.py

Writes `out/gifts_donors.csv` (one row per donor party-year) and `out/gifts_reconcile.csv` (per party-year:
published total, extracted total, delta). **The reconciliation is the ingest gate**: every party-year must tie
to the total the same page publishes, or the script says so. 61 party-years, 0 mismatches on 2026-11-20.

Override the output directory with `AERARIUM_GIFTS_OUT`.

## 2. `export_view.py` — the page's single input

Reads `out/party-line-disclosure.csv` (budget series), the two gift CSVs, the live `/dashboard/subsidies`
table, and `data/aerarium.duckdb` for chapter V. Writes `out/view-data.json`.

    .venv/bin/python scripts/export_view.py

Rules it enforces so the page cannot lie:

- `named_k` / `anon_k` are `null` where `r4` is `not-published`. The recipient register covers 2017-2024, so a
  year outside it has no split to report; zero would be a claim.
- Donor names keep their published spelling. Only runs of whitespace are normalised, because embedded
  newlines split one donor into two.
- NFRP rows are grouped **by KvK**, not by name. The register spells one recipient several ways; rows sharing
  a KvK are one entity, and every variant is kept in `variants` so the merge can be checked. Where KvK is
  null, no merge is attempted.
- `years` are integers in `edges[]` and `nfrp[]`, strings as JSON object keys. Mixing them is a trap for the
  consumer.

## 3. `reembed_view.py` — data into the page

`out/index.html` is self-contained: it carries the JSON inline so it renders from `file://` with no fetch.
This script replaces that block and refuses to write unless the new block parses back equal to the file.

    .venv/bin/python scripts/reembed_view.py

Run it after every `export_view.py`. It is idempotent: same JSON in, byte-identical page out.

## `fetch_corpus.sh` — the annual-report corpus

Downloads all 92 `jaarverslagen` documents and extracts text with `pdftotext`, then deletes the PDFs. Text is
what is kept; the PDFs are re-fetchable.

Two link shapes have to be handled. 2022-2024 rows link straight to `.../documenten/<uuid>/file`. 2020-2021 rows
link to `/details/ronl-<hash>`, a JavaScript shell that returns 607 bytes of HTML to curl, so the visible link
is not the document. The file is behind the site's own attachment endpoint, which needs no key:

    https://open.overheid.nl/overheid/openbaarmakingen/api/v0/attachment/ronl-<hash>

Filenames carry a hash of the link (`<jaar>_<partij>_<deel>_<hash8>.txt`) because the register holds two
distinct 2021 Volt deel-2 documents with the same year, party and deel; without the hash one overwrites the
other and the loss is invisible. 92 documents, 92 files.

Verify a fetch by content type or PDF magic bytes, never by HTTP status alone: the details pages return 200
with an HTML body.

The extracted text of all 92 documents is committed under `corpus/text/` with the register index at
`corpus/index.tsv`, so the findings do not depend on a refetch or on a temporary directory. Re-running the
script regenerates it.

## Checking the numbers

    .venv/bin/python scripts/verify_findings.py

Asserts every figure FINDING-002 and FINDING-003 state, against `view-data.json`, the store and the corpus,
and exits non-zero on any disagreement. Prose and data drift apart silently otherwise; a number that is not
asserted here is not verified.
