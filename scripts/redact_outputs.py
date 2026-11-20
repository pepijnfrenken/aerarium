#!/usr/bin/env python3
"""Produce the publishable donor file: same rows, without the personal address columns.

`out/gifts_donors.csv` keeps everything the register publishes, including each donor's street address and the
UBO's place of residence. That file stays local. This script writes the version that goes into the repository
and onto the public page.

The line is: name, amount, date and recipient are what the Wfpp publishes these contributions *for* —
accountability about who funds a party. A street address of a private individual is not needed to balance that
book, and a public list of "person + home address + political donation" is a target list. So the address
columns are dropped, and nothing else is.

Everything else is preserved, including names and UBO names, because anonymising individuals would defeat the
purpose of the register and of this project.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "out" / "gifts_donors.csv"
DST = REPO / "out" / "gifts_donors_public.csv"
DROP = {"adres", "ubo_plaats"}


def main() -> int:
    if not SRC.exists():
        print(f"missing {SRC}; run scripts/extract_gifts.py first", file=sys.stderr)
        return 1

    with SRC.open(newline="", encoding="utf-8") as src, DST.open("w", newline="", encoding="utf-8") as dst:
        reader = csv.DictReader(src)
        fields = [c for c in reader.fieldnames or [] if c not in DROP]
        writer = csv.DictWriter(dst, fieldnames=fields)
        writer.writeheader()
        rows = 0
        for row in reader:
            writer.writerow({k: row.get(k, "") for k in fields})
            rows += 1

    dropped = [c for c in DROP if c in (csv.DictReader(SRC.open(encoding="utf-8")).fieldnames or [])]
    print(f"wrote {DST} ({DST.stat().st_size:,} bytes), {rows} rows")
    print(f"dropped columns: {dropped or 'none present'}")
    print(f"kept columns: {fields}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
