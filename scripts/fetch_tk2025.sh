#!/usr/bin/env bash
# Fetch the BZK gift overviews for the Tweede Kamer election of 29 October 2025.
#
# These are ODS spreadsheets on rijksoverheid.nl under /site/binaries/. Dropping the /site/ segment returns an
# HTML 404 page with status 200, so check the content type, never just the status code.
set -uo pipefail

OUT="$(cd "$(dirname "$0")/.." && pwd)/data/raw/tk2025"
mkdir -p "$OUT"

BASE="https://www.rijksoverheid.nl/site/binaries/site-content/collections/documents/2025/10/22/giften-en-schulden-van-partijen-en-kandidaten-voor-de-tweede-kamerverkiezing-2025"

FILES=(
  "overzicht-giften-aan-politieke-partijen-tweede-kamerverkiezing-2025.ods"
  "overzicht-giften-aan-kandidaten-tweede-kamerverkiezing-2025.ods"
  "overzicht-schulden-van-politieke-partijen-tweede-kamerverkiezing-2025.ods"
)

for f in "${FILES[@]}"; do
  dest="$OUT/$f"
  if [ -s "$dest" ] && [ "$(file -b --mime-type "$dest")" = "application/vnd.oasis.opendocument.spreadsheet" ]; then
    printf "skip %s (present)\n" "$f"
    continue
  fi
  curl -sSL -m 120 -A "Mozilla/5.0" -o "$dest" "$BASE/$f"
  mime="$(file -b --mime-type "$dest")"
  if [ "$mime" != "application/vnd.oasis.opendocument.spreadsheet" ]; then
    printf "FAIL %s: got %s, not a spreadsheet\n" "$f" "$mime"
    rm -f "$dest"
    continue
  fi
  printf "ok   %s (%s)\n" "$f" "$(du -h "$dest" | cut -f1)"
done
