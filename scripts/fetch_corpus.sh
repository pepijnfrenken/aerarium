#!/usr/bin/env bash
# Fetch the 92 party annual reports, extract text, then delete the PDFs.
# Text is small and is what we keep; the PDFs are re-fetchable from open.overheid.nl.
set -uo pipefail

# Paths live under the repo, not /tmp. The old version staged the corpus in /tmp and read its index from
# /tmp/jaarverslagen.json, so the step that produced the index and the step that consumed it had no declared handoff:
# on a clean machine the fetch read a file nothing had written, and on this one it worked only because a stale file
# was still there. Both are overridable, and a missing index is an error rather than an empty fetch.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORPUS="${AERARIUM_CORPUS:-$ROOT/corpus/jaarverslagen}"
INDEX_SRC="${AERARIUM_JAARVERSLAGEN:-$CORPUS/index-source.json}"
TEXT="$CORPUS/text"
PDF="$CORPUS/pdf"
mkdir -p "$TEXT" "$PDF"

if [ ! -f "$INDEX_SRC" ]; then
  echo "missing index: $INDEX_SRC" >&2
  echo "set AERARIUM_JAARVERSLAGEN to the JSON list of annual reports, or place it at that path" >&2
  exit 1
fi

python3 - "$INDEX_SRC" > "$CORPUS/index.tsv" <<'PY'
import json, sys
rows = json.load(open(sys.argv[1]))
for r in rows:
    print(f"{r['jaar']}\t{r['partij']}\t{r['deel']}\t{r['pages']}\t{r['link']}")
PY

total=$(wc -l < "$CORPUS/index.tsv")
echo "documents to fetch: $total"
n=0
while IFS=$'\t' read -r jaar partij deel pages link; do
  n=$((n+1))
  slug=$(printf '%s' "$partij" | tr ' /' '__' | tr -cd 'A-Za-z0-9_')
  # The register carries two distinct documents for 2021 Volt deel 2 (different ronl-ids, same party/deel),
  # so a name built only from year, party and deel silently overwrites one with the other. The link hash makes
  # every filename unique and stable.
  lh=$(printf '%s' "$link" | sha256sum | cut -c1-8)
  pdf="$PDF/${jaar}_${slug}_${deel}_${lh}.pdf"
  txt="$TEXT/${jaar}_${slug}_${deel}_${lh}.txt"
  if [ -s "$txt" ]; then
    printf "[%02d/%s] skip %s\n" "$n" "$total" "$(basename "$txt")"
    continue
  fi
  # 2020-2021 rows link to /details/ronl-<hash>, a JavaScript shell that returns 607 bytes of HTML to curl.
  # The document itself is served by the site's own attachment endpoint, which needs no auth:
  #   https://open.overheid.nl/overheid/openbaarmakingen/api/v0/attachment/ronl-<hash>
  case "$link" in
    */details/ronl-*)
      ronl="${link##*/details/}"
      link="https://open.overheid.nl/overheid/openbaarmakingen/api/v0/attachment/${ronl}"
      ;;
  esac
  code=$(curl -sSL --http1.1 -m 240 -A "Mozilla/5.0 (X11; Linux x86_64)" -o "$pdf" -w '%{http_code}' "$link")
  if [ "$code" != "200" ] || [ ! -s "$pdf" ]; then
    printf "[%02d/%s] FAIL %s http=%s\n" "$n" "$total" "$partij $jaar" "$code"
    rm -f "$pdf"
    continue
  fi
  # -layout keeps the table columns readable; form feeds (\f) mark page breaks
  if pdftotext -layout "$pdf" "$txt" 2>/dev/null; then
    chars=$(wc -c < "$txt")
    printf "[%02d/%s] ok %s %s pages=%s chars=%s\n" "$n" "$total" "$jaar" "$partij" "$pages" "$chars"
  else
    printf "[%02d/%s] PDFTOTEXT-FAIL %s %s\n" "$n" "$total" "$jaar" "$partij"
  fi
  rm -f "$pdf"
done < "$CORPUS/index.tsv"

echo
echo "text files: $(ls -1 "$TEXT" | wc -l)  total bytes: $(du -sb "$TEXT" | cut -f1)"
echo "pdf dir (should be empty): $(ls -1 "$PDF" | wc -l) files, $(du -sh "$PDF" | cut -f1)"
