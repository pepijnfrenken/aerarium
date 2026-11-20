#!/usr/bin/env python3
"""Re-embed out/view-data.json into out/index.html's inline <script type="application/json" id="data">.

The page is self-contained by design (no fetch, works from file://), so the data block is a copy of the JSON.
Any change to the export has to be written into the page, or the page silently keeps showing yesterday's numbers.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "out" / "view-data.json"
PAGE = REPO / "out" / "index.html"

BLOCK = re.compile(r'(<script[^>]*id="data"[^>]*>)(.*?)(</script>)', re.S)


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    page = PAGE.read_text(encoding="utf-8")

    m = BLOCK.search(page)
    if not m:
        print("FAIL: no <script id=\"data\"> block in index.html", file=sys.stderr)
        return 1
    old_len = len(m.group(2))
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    new_page = page[: m.start(2)] + payload + page[m.end(2) :]

    # Prove the block parses before touching the file.
    m2 = BLOCK.search(new_page)
    parsed = json.loads(m2.group(2))
    assert parsed == data, "roundtrip mismatch"

    PAGE.write_text(new_page, encoding="utf-8")
    print(f"embedded JSON: {old_len:,} -> {len(payload):,} chars")
    print(f"page: {len(page):,} -> {len(new_page):,} bytes")
    print(f"parties={len(parsed['subsidy']['parties'])} donors={len(parsed['gifts']['donors'])} "
          f"cross={len(parsed['gifts']['cross_party'])} budget={len(parsed['budget'])} nfrp={len(parsed['nfrp'])} "
          f"rules={len(parsed['meta']['rules'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
