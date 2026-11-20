#!/usr/bin/env bash
# Fetch the 92 party annual reports, extract text, then delete the PDFs.
# Text is small and is what we keep; the PDFs are re-fetchable from open.overheid.nl.
set -uo pipefail

CORPUS=/tmp/aerarium-corpus
TEXT="$CORPUS/text"
PDF="$CORPUS/pdf"
mkdir -p "$TEXT" "$PDF"

python3 - <<'PY' > "$CORPUS/index.tsv"
import json
rows = json.load(open('/tmp/jaarverslagen.json'))
for r in rows:
    print(f"{r['jaar']}\t{r['partij']}\t{r['deel']}\t{r['pages']}\t{r['link']}")
PY

total=$(wc -l < "$CORPUS/index.tsv")
echo "documents to fetch: $total"
n=0
while IFS=$'\t' read -r jaar partij deel pages link; do
  n=$((n+1))
  slug=$(printf '%s' "$partij" | tr ' /' '__' | tr -cd 'A-Za-z0-9_')
  pdf="$PDF/${jaar}_${slug}_${deel}.pdf"
  txt="$TEXT/${jaar}_${slug}_${deel}.txt"
  if [ -s "$txt" ]; then
    printf "[%02d/%s] skip %s\n" "$n" "$total" "$(basename "$txt")"
    continue
  fi
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
