#!/usr/bin/env python3
"""Extract donor-level gifts for every party-year from the dashboard's RSC payload.

The per-party page server-renders an empty table but ships the rows inside the Next.js RSC payload as
`giften_totaal` objects. No browser needed. Every party-year is reconciled against the total the same page
publishes for that party, and any party-year that does not reconcile is reported, never silently kept.

Outputs:
  /tmp/aerarium-corpus/gifts_donors.csv     one row per donor party-year (+ nested contributions)
  /tmp/aerarium-corpus/gifts_reconcile.csv  per party-year: published total, extracted total, delta
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://www.partijfinanciering.nl"
OUT = Path(os.environ.get("AERARIUM_GIFTS_OUT", str(Path(__file__).resolve().parents[1] / "out")))
UA = {"User-Agent": "aerarium/0.1 (public-register join; provenance research)"}
YEARS = (2022, 2023, 2024)


def get(url: str) -> tuple[str, str, int]:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        body = r.read()
    return body.decode("utf-8", "replace"), hashlib.sha256(body).hexdigest(), len(body)


def dutch(text: str) -> float | None:
    s = re.sub(r"\s+", "", text.replace("€", "").replace("\xa0", ""))
    if s in ("", "-", "–", "0,00"):
        return None if s in ("", "-", "–") else 0.0
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def cards(page: str) -> list[tuple[str, float | None, str]]:
    """(party, published total, href) for every party card on a year index page."""
    out = []
    for chunk in page.split('data-slot="card"')[1:]:
        m = re.search(r"<h2[^>]*>(.*?)</h2>", chunk, re.S)
        a = re.search(r"Totaal ontvangen bijdragen.*?<span[^>]*>€\s*(?:<!-- -->)?\s*([\d.,]+)", chunk, re.S)
        l = re.search(r'href="([^"]+)"', chunk)
        if m and a and l:
            out.append((re.sub(r"\s+", " ", m.group(1)).strip(), dutch(a.group(1)), l.group(1)))
    return out


def records(page: str) -> list[dict]:
    out = []
    for m in re.finditer(r'\\"__typename\\":\\"giften_totaal\\"', page):
        start = page.rfind("{", 0, m.start())
        end = page.find("}", m.end())
        if start < 0 or end < 0:
            continue
        raw = page[start:end + 1].replace("\\\\", "\\").replace('\\"', '"')
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows: list[dict] = []
    recon: list[dict] = []

    for year in YEARS:
        idx_url = f"{BASE}/dashboard/jaarlijkse-verantwoording/giften/{year}"
        page, sha, n = get(idx_url)
        cs = cards(page)
        published = sum(v for _, v, _ in cs if v is not None)
        print(f"{year}: {len(cs)} party cards, published sum €{published:,.2f} (index {n}B sha {sha[:8]})")
        for party, pub_total, href in cs:
            url = BASE + href
            try:
                detail, dsha, dn = get(url)
            except Exception as exc:  # noqa: BLE001
                recon.append(dict(jaar=year, partij=party, published=pub_total, extracted=None,
                                  delta=None, status=f"fetch-error: {exc}", url=url))
                print(f"  {party:<10} FAIL {exc}")
                continue
            recs = records(detail)
            summ = [r for r in recs if r.get("totaal") is not None]
            extracted = round(sum(float(r["totaal"]) for r in summ), 2)
            delta = None if pub_total is None else round(extracted - pub_total, 2)
            status = "ok" if delta is not None and abs(delta) < 0.01 else ("no-published-total" if pub_total is None else "MISMATCH")
            recon.append(dict(jaar=year, partij=party, published=pub_total, extracted=extracted,
                              delta=delta, status=status, url=url))
            print(f"  {party:<10} published {pub_total} extracted {extracted} delta {delta} {status}"
                  f" records={len(recs)} donors={len({r.get('naam_donateur') for r in summ})}")
            for r in recs:
                rows.append(dict(
                    jaar=r.get("jaar") or year,
                    partij=r.get("partij") or party,
                    slug=r.get("slug"),
                    neveninstelling=r.get("neveninstelling"),
                    donor=r.get("naam_donateur"),
                    adres=r.get("adres_gever"),
                    ubo_naam=r.get("naam_ubo"),
                    ubo_plaats=r.get("woonplaats_ubo"),
                    datum=r.get("datum"),
                    bedrag_gt_1000=r.get("bedragen_groter_1000"),
                    totaal=r.get("totaal"),
                    kind="donor-total" if r.get("totaal") is not None else "contribution",
                    source_url=url,
                    retrieved_at=now,
                ))
            time.sleep(0.4)

    rows_path = OUT / "gifts_donors.csv"
    with rows_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    rec_path = OUT / "gifts_reconcile.csv"
    with rec_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(recon[0].keys()))
        w.writeheader()
        w.writerows(recon)

    bad = [r for r in recon if r["status"] != "ok"]
    print(f"\nrows={len(rows)} party-years={len(recon)} mismatches={len(bad)}")
    for b in bad[:10]:
        print("  !!", b)
    print(f"wrote {rows_path} and {rec_path}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
