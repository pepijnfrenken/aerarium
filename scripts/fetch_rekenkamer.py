#!/usr/bin/env python3
"""Harvest the Rekenkamer publication register: page metadata, then report PDFs.

Why this exists: rung 6 of the chain attaches a Rekenkamer finding to a budget line. PROBE-008
established there is no machine-readable feed — no API, no JSON endpoint, `/over-de-rekenkamer/
open-data` 404 — so a finding is a PDF with a title and a date, and attaching one to an article is
document classification, not a key join. This script does the harvesting half of that.

Enumeration is from the site's own sitemap index (robots.txt points at it and disallows nothing),
not from link-scraping, so coverage is whatever the publisher declares rather than what a crawler
happened to reach.

Bounds, stated so the output can be read honestly:
  * one host only, `www.rekenkamer.nl`;
  * metadata pass: every non-video `/documenten/YYYY/...` page from YEARS_FROM onward;
  * PDF pass: at most MAX_PDFS files, chosen by rule, never by what happened to download first;
  * 4 concurrent connections, 0.2 s jitter between requests, one retry then a recorded failure;
  * everything lands in corpus/rekenkamer/ which is gitignored. PDFs are disposable; the extracted
    text and the metadata JSONL are the artifacts, and both are regenerable by re-running this.

Resumable: pages and PDFs already recorded are skipped, so a killed run costs only what it had left.
"""
from __future__ import annotations

import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "rekenkamer"
URLS = CORPUS / "urls.json"
PAGES = CORPUS / "pages.jsonl"
PDFS = CORPUS / "pdf"
PDF_INDEX = CORPUS / "pdfs.json"

SITEMAP = "https://www.rekenkamer.nl/sitemap.xml"
YEARS_FROM = 2016
MAX_PDFS = 400
WORKERS = 1
UA = {"User-Agent": "aerarium/0.1 (public money provenance; github.com/pepijnfrenken/aerarium)"}


def fetch(url: str, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


BLOCKED = {"hit": False}


def polite_fetch(url: str, tries: int = 2) -> tuple[str | None, str | None]:
    """Return (body, error). One second between requests; a 403 stops the whole pass.

    The first version used four connections at roughly seven requests a second and the host answered 403 in
    27 ms from then on. A block is a message to slow down, not an obstacle to route around, so this stops
    rather than retrying into it: whatever was harvested stays, the failures stay marked as failures, and
    the next run resumes when the block has lifted.
    """
    if BLOCKED["hit"]:
        return None, "skipped: run stopped after a block"
    last = None
    for _ in range(tries):
        try:
            time.sleep(1.0 + random.random() * 0.3)
            return fetch(url), None
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 403:
                BLOCKED["hit"] = True
                return None, "HTTP 403: blocked, pass stopped"
            if e.code in (404, 410):
                return None, last
        except Exception as e:
            last = type(e).__name__
    return None, last


def fetch_bytes(url: str, timeout: int = 60) -> bytes:
    """PDFs are binary. Decoding them as text and re-encoding corrupts the file, so this path never decodes."""
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def polite_fetch_bytes(url: str, tries: int = 2) -> tuple[bytes | None, str | None]:
    last = None
    for _ in range(tries):
        try:
            time.sleep(0.2 + random.random() * 0.3)
            return fetch_bytes(url), None
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (403, 404, 410):
                return None, last
        except Exception as e:
            last = type(e).__name__
    return None, last


def harvest_urls() -> list[str]:
    """Rebuild corpus/rekenkamer/urls.json from the sitemap index if it is missing."""
    if URLS.exists():
        return json.loads(URLS.read_text(encoding="utf-8"))
    idx = fetch(SITEMAP)
    subs = re.findall(r"<loc>([^<]+)</loc>", idx)
    out: list[str] = []
    for s in subs:
        try:
            out.extend(re.findall(r"<loc>([^<]+)</loc>", fetch(s)))
        except Exception as e:
            print(f"  sitemap failed {s}: {e}", file=sys.stderr)
    out = list(dict.fromkeys(out))
    URLS.write_text(json.dumps(out, indent=0), encoding="utf-8")
    return out


def document_pages(urls: list[str]) -> list[str]:
    keep = []
    for u in urls:
        m = re.search(r"/documenten/(\d{4})/", u)
        if not m or "/videos/" in u:
            continue
        if int(m.group(1)) < YEARS_FROM:
            continue
        keep.append(u)
    return keep


def parse_page(url: str, body: str) -> dict:
    title = re.search(r'"pageTitle":"([^"]{0,300})"', body)
    date = re.search(r'"publicationDate":"([^"]+)"', body)
    ctype = re.search(r'"contentType":"([^"]+)"', body)
    pdfs = list(dict.fromkeys(re.findall(r'(https?://[^"\'\s]+?\.pdf)', body)))
    jaar = re.search(r"/documenten/(\d{4})/", url)
    # Every PDF the page links, plus whether the page itself is the download wrapper.
    return {
        "url": url,
        "slug": url.rstrip("/").split("/")[-1],
        "jaar": int(jaar.group(1)) if jaar else None,
        "title": title.group(1) if title else None,
        "date": date.group(1) if date else None,
        "content_type": ctype.group(1) if ctype else None,
        "pdfs": pdfs,
        "n_pdfs": len(pdfs),
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def harvest_pages(pages: list[str]) -> int:
    # A row with an error is NOT done: treating it as done would freeze a transient block into a permanent
    # hole in the corpus, and the corpus would silently be a sample of whatever happened to succeed.
    done = {r["url"] for r in load_jsonl(PAGES) if not r.get("error")}
    todo = [u for u in pages if u not in done]
    print(f"page metadata: {len(done)} done, {len(todo)} to fetch of {len(pages)}")
    if not todo:
        return 0
    ok = failed = 0
    with PAGES.open("a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(polite_fetch, u): u for u in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            u = futs[fut]
            body, err = fut.result()
            if body is None:
                rec = {"url": u, "error": err, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                failed += 1
            else:
                rec = parse_page(u, body)
                ok += 1
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 200 == 0:
                fh.flush()
                print(f"  {i}/{len(todo)}  ok {ok}  failed {failed}")
    print(f"page metadata complete: ok {ok}, failed {failed}")
    return failed


def choose_pdfs(rows: list[dict]) -> list[dict]:
    """Pick which PDFs to download, by stated rule.

    Every page with a PDF is a candidate, newest first within each year, one PDF per page (the first
    link). Newest-first is the rule because a finding attaches to the budget line of its year, and the
    cap is applied to the ranked list rather than to arrival order.
    """
    cands = []
    for r in rows:
        if r.get("error") or not r.get("pdfs"):
            continue
        cands.append({"url": r["pdfs"][0], "page": r["url"], "jaar": r["jaar"],
                      "title": r.get("title"), "date": r.get("date")})
    cands.sort(key=lambda c: (c["date"] or "", c["page"]), reverse=True)
    return cands[:MAX_PDFS]


def harvest_pdfs(rows: list[dict]) -> None:
    PDFS.mkdir(parents=True, exist_ok=True)
    index = json.loads(PDF_INDEX.read_text(encoding="utf-8")) if PDF_INDEX.exists() else {}
    todo = [c for c in choose_pdfs(rows) if c["url"] not in index]
    print(f"pdfs: {len(index)} recorded, {len(todo)} to fetch (cap {MAX_PDFS})")
    if not todo:
        return
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(polite_fetch_bytes, c["url"]): c for c in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            c = futs[fut]
            body, err = fut.result()
            if body is None:
                index[c["url"]] = {**c, "error": err}
            elif not body.startswith(b"%PDF"):
                # A 200 that is not a PDF is the failure mode this project has already been bitten by
                # twice: an HTML error page served with a success status.
                index[c["url"]] = {**c, "error": f"not a PDF ({body[:16]!r})", "bytes": len(body)}
            else:
                name = re.sub(r"[^A-Za-z0-9._-]+", "-", c["url"].rstrip("/").split("/")[-1])[:120]
                path = PDFS / f"{c['jaar']}-{name}"
                path.write_bytes(body)
                index[c["url"]] = {**c, "file": str(path.relative_to(ROOT)), "bytes": len(body)}
            if i % 50 == 0:
                print(f"  {i}/{len(todo)}")
    PDF_INDEX.write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
    got = sum(1 for v in index.values() if v.get("file"))
    print(f"pdfs complete: {got} downloaded, {len(index) - got} failed")


def main() -> int:
    CORPUS.mkdir(parents=True, exist_ok=True)
    urls = harvest_urls()
    pages = document_pages(urls)
    print(f"document pages {YEARS_FROM}+: {len(pages)}")
    if "--pages" in sys.argv or "--all" in sys.argv:
        harvest_pages(pages)
    if "--pdfs" in sys.argv or "--all" in sys.argv:
        harvest_pdfs(load_jsonl(PAGES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
