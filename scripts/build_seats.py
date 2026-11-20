#!/usr/bin/env python3
"""Seat counts per party, for the three Tweede Kamer elections that fall in the money window.

Source is the Kiesraad's own announcement of the official result for each election, not a news summary:

  2021-03-17  https://www.kiesraad.nl/actueel/nieuws/2021/03/26/officiele-uitslag-tweede-kamerverkiezing-17-maart-2021
  2023-11-22  https://www.kiesraad.nl/actueel/nieuws/2023/12/01/kiesraad-stelt-uitslag-tweede-kamerverkiezing-22-november-2023-vast
              (definitive numbers as established at the second sitting, 4 December 2023)
  2025-10-29  https://www.kiesraad.nl/actueel/nieuws/2025/11/7/kiesraad-uitslag-tweede-kamerverkiezing-betrouwbaar
              (established 7 November 2025)

Each list must sum to 150 seats. That is asserted here, so a typo cannot travel quietly into a per-seat figure.

A list is not a filer. GroenLinks and PvdA filed separate financial reports in every year but ran one list in 2023
and 2025, so their seats belong to the list and are carried once, under GL-PvdA. Splitting 20 seats between two
filers would be an invented number, so it is not done.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "out" / "seats.json"

ELECTIONS = {
    "2021": {
        "date": "2021-03-17",
        "source": ("https://www.kiesraad.nl/actueel/nieuws/2021/03/26/"
                   "officiele-uitslag-tweede-kamerverkiezing-17-maart-2021"),
        "seats": {"VVD": 34, "D66": 24, "PVV": 17, "CDA": 15, "SP": 9, "PvdA": 9, "GL": 8, "FvD": 8,
                  "PvdD": 6, "CU": 5, "Volt": 3, "JA21": 3, "SGP": 3, "DENK": 3, "50PLUS": 1, "BBB": 1,
                  "BIJ1": 1},
    },
    "2023": {
        "date": "2023-11-22",
        "source": ("https://www.kiesraad.nl/actueel/nieuws/2023/12/01/"
                   "kiesraad-stelt-uitslag-tweede-kamerverkiezing-22-november-2023-vast"),
        "seats": {"VVD": 24, "D66": 9, "GL-PvdA": 25, "PVV": 37, "CDA": 5, "SP": 5, "FvD": 3, "PvdD": 3,
                  "CU": 3, "Volt": 2, "JA21": 1, "SGP": 3, "DENK": 3, "BBB": 7, "NSC": 20},
    },
    "2025": {
        "date": "2025-10-29",
        "source": ("https://www.kiesraad.nl/actueel/nieuws/2025/11/7/"
                   "kiesraad-uitslag-tweede-kamerverkiezing-betrouwbaar"),
        "seats": {"D66": 26, "PVV": 26, "VVD": 22, "GL-PvdA": 20, "CDA": 18, "JA21": 9, "FvD": 7, "BBB": 4,
                  "DENK": 3, "CU": 3, "SP": 3, "SGP": 3, "PvdD": 3, "50PLUS": 2, "Volt": 1},
    },
}

# The money sources name filers; seats belong to lists. Only this pair needs joining.
LIST_OF_FILER = {"GL": "GL-PvdA", "PvdA": "GL-PvdA"}


def main() -> int:
    payload = {"meta": {
        "unit": "zetels in de Tweede Kamer, 150 total",
        "source": "Kiesraad, official result of each election",
        "note": ("Seats belong to a list. GroenLinks and PvdA filed separate financial reports throughout but "
                 "ran one list in 2023 and 2025, so their seats are carried once under GL-PvdA."),
        "list_of_filer": LIST_OF_FILER,
    }, "elections": {}}

    for year, e in ELECTIONS.items():
        total = sum(e["seats"].values())
        if total != 150:
            print(f"FAIL {year}: seats sum to {total}, not 150", file=sys.stderr)
            return 1
        payload["elections"][year] = {"date": e["date"], "source": e["source"], "total": total,
                                      "seats": dict(sorted(e["seats"].items(), key=lambda kv: -kv[1]))}
        print(f"{year} ({e['date']}): {len(e['seats'])} lists, {total} seats  ok")

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT} ({OUT.stat().st_size:,} bytes)")
    print("\n2025 seats:", ", ".join(f"{k} {v}" for k, v in payload["elections"]["2025"]["seats"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
