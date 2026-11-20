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

## `fetch_corpus.sh` — the annual-report corpus (partial)

Downloads the 92 `jaarverslagen` documents and extracts text with `pdftotext`. Fetches 2022-2024 (58 documents)
successfully. **2020-2021 fail by design of the source**: those rows link to
`open.overheid.nl/details/ronl-…`, a JavaScript shell that returns 607 bytes of HTML to a plain fetch. They
need a browser or the open.overheid API; the script does not fake a success when the content type says HTML.

## Checking the numbers

`verify_finding002.py` in the scratch directory asserts every figure FINDING-002 states against
`view-data.json` and the store, and exits non-zero on any disagreement. Prose and data drift apart silently
otherwise.
