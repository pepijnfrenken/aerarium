#!/usr/bin/env python3
"""Embed the exported payloads into out/index.html.

The page is self-contained by design (no fetch, works from file://), so the data blocks are copies of the JSON.
Any change to an export has to be written into the page, or the page silently keeps showing yesterday's numbers.

Two payloads, deliberately separate:

  <script type="application/json" id="data">        the party side, from out/view-data.json
  <script type="application/json" id="state-data">  the state side, from out/state-data.json

The second block is `state-data`, not `state`: the page also has `<section id="state">`, and two elements cannot
share an id. They did for one build, and getElementById returned the section, whose textContent is markup rather
than JSON, so the section rendered nothing while the Python side saw a perfect payload.

They are kept apart rather than merged because their lifecycles differ: the party side is rebuilt by
scripts/export_view.py, the state side by scripts/build_state_payload.py, and a build that merges them would let a
missing input silently blank half the page instead of failing. A missing state artifact is an error here, not an
empty section.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "out"
PAGE = OUT / "index.html"

BLOCKS = [("data", "view-data.json"), ("state-data", "state-data.json")]


def block_re(bid: str) -> re.Pattern:
    return re.compile(r'(<script[^>]*id="' + re.escape(bid) + r'"[^>]*>)(.*?)(</script>)', re.S)


def encode(obj) -> str:
    # `</` inside JSON would close the script element early, so it is escaped.
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def main() -> int:
    page = PAGE.read_text(encoding="utf-8")
    original_len = len(page)
    summary: list[str] = []

    for bid, filename in BLOCKS:
        path = OUT / filename
        if not path.exists():
            print(f"FAIL: {filename} is missing; refusing to embed a partial page", file=sys.stderr)
            return 1
        data = json.loads(path.read_text(encoding="utf-8"))
        payload = encode(data)
        rx = block_re(bid)
        m = rx.search(page)
        if not m:
            if bid != "state-data":
                print(f'FAIL: no <script id="{bid}"> block in index.html', file=sys.stderr)
                return 1
            # Insert the state block immediately before the app script, so it exists in the document before the
            # script that reads it. Creating it here keeps the page's markup out of the data path.
            anchor = re.search(r'<script src="assets/app\.js"></script>', page)
            if not anchor:
                print("FAIL: could not find the app script tag to anchor the state block", file=sys.stderr)
                return 1
            new_block = f'<script type="application/json" id="state-data">{payload}</script>\n'
            page = page[: anchor.start()] + new_block + page[anchor.start():]
            old_len = 0
        else:
            old_len = len(m.group(2))
            page = page[: m.start(2)] + payload + page[m.end(2):]

        # Prove every block still parses before writing anything.
        check = rx.search(page)
        if not check:
            print(f"FAIL: block {bid} vanished during the rewrite", file=sys.stderr)
            return 1
        parsed = json.loads(check.group(2))
        assert parsed == data, f"roundtrip mismatch in block {bid}"
        summary.append(f"  {bid}: {old_len:,} -> {len(payload):,} chars")

    PAGE.write_text(page, encoding="utf-8")
    print("embedded payloads:")
    print("\n".join(summary))
    print(f"page: {original_len:,} -> {len(page):,} bytes")
    view_match = block_re("data").search(page)
    if not view_match:
        print("FAIL: data block missing after the rewrite", file=sys.stderr)
        return 1
    view = json.loads(view_match.group(2))
    print(f"parties={len(view['subsidy']['parties'])} donors={len(view['gifts']['donors'])} "
          f"cross={len(view['gifts']['cross_party'])} budget={len(view['budget'])} nfrp={len(view['nfrp'])} "
          f"rules={len(view['meta']['rules'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
