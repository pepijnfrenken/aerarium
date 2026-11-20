#!/usr/bin/env python3
"""Extract the neveninstellingen that each party names in its Wfpp annual report.

Three presentation shapes carry almost all of it:

  bullet list   "... overzicht ... van de neveninstellingen van de VVD:" then "- Stichting X;" lines
  amount table  "De totaalbedragen van de uitgegeven subsidie per entiteit zijn:" then "Name  EUR amount"
  inline figure a bullet whose figure sits on the same line: "Stichting Huisvesting CDA 603.243"

The rule this script obeys: a row exists only where the document names the entity. No amount is computed,
allocated or inferred. A named entity with no figure gets an empty amount, and the count of those is reported,
because "named but unquantified" is the common case and hiding it would flatter the disclosure.

Names are never normalised or merged. If a report writes 'Wierdi Beckmanstichting', that is the value.

Precision beats recall. Prose that merely mentions the word neveninstelling is rejected by looks_like_name(),
so this under-reports rather than filling the file with sentence fragments.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEXT = REPO / "corpus" / "text"
OUT = REPO / "out" / "neveninstellingen.csv"
FIELDS = ["partij", "jaar", "entiteit", "soort", "bedrag_eur", "evidence_quote", "bron_bestand"]

ENTITY_HINT = re.compile(
    r"(stichting|vereniging|fonds|foundation|instituut|institute|bureau|jovd|jonge |cdja|perspectief|"
    r"jongeren|scientific|wetenschappelijk|academie|centrum)",
    re.I,
)
BULLET = re.compile(r"^\s*[-•–]\s*(.{3,90}?)\s*[;,]?\s*$")
TABLEROW = re.compile(r"^\s{0,6}(\S.{2,80}?)\s{2,}€?\s*([0-9][0-9.]*(?:,[0-9]{2})?)\s*$")
TRAILING_NUMBER = re.compile(
    r"^(.*?)\s+€?\s*([0-9]{1,3}(?:\.[0-9]{3})+(?:,[0-9]{2})?|[0-9]{1,3}(?:,[0-9]{3})+|[0-9]{3,}(?:,[0-9]{2})?)$"
)
LIST_MARKER = re.compile(r"^(\d+[\).]|\d+(?:\.\d+)+)\s*")
# "Rekening-courant Jongerenorganisatie Forum voor Democratie" is a ledger label: the entity is what follows it.
LEDGER_LABEL = re.compile(r"^(rekening-?courant|r/c|rk)\s+(van\s+de\s+)?", re.I)
ARTICLE = re.compile(r"^(de|het|een|ons|onze|haar|zijn|hun)\s+", re.I)
STOPWORDS = re.compile(
    r"\b(is|zijn|heeft|hebben|wordt|worden|gebeurt|blijkt|geldt|betreft|ontvangen|afgelegd|afleggen|"
    r"verantwoording|neveninstellingen|neveninstelling|beide|deze|die|dit|dat|niet|ook|aan|door|met|"
    r"subsidie|giften|artikel|conform|jaarrekening|accountant|bestuur|welke|waarvan|alsmede)\b",
    re.I,
)
NOT_A_NAME = re.compile(
    r"^(oprichting|kosten|totaal|bijdrage|saldo|subsidie|giften|overzicht|doel|stand|leden|contributie|"
    r"resultaat|opbrengsten|lasten|personeel|activiteiten|mutatie|verplichting|vordering|schuld|bedrag|"
    r"nr|nummer|datum|jaar)\b",
    re.I,
)
CONNECTOR = {"van", "de", "der", "den", "voor", "het", "in", "en", "of", "ter", "bij", "op", "tot", "aan"}

# The register spells one party differently across years, so a raw party string splits an entity's history in
# two. Canonical keys, with the raw string still recoverable from bron_bestand.
PARTY_CANON = {
    "FVD": "FvD", "GroenLinks": "GL", "ChristenUnie": "CU", "50plus": "50PLUS",
    "PvdA": "PvdA", "PvdD": "PvdD",
}


def looks_like_name(raw: str) -> bool:
    """A party's neveninstelling is a proper name, not a sentence."""
    s = ARTICLE.sub("", raw.strip(" .;:,"))
    if not (3 <= len(s) <= 80):
        return False
    if ":" in s or re.search(r"[.!?]\s", s):
        return False
    words = s.split()
    if len(words) > 9:
        return False
    if STOPWORDS.search(s):
        return False
    if not re.match(r"^[A-Z0-9]", s):
        return False
    return any(w[0].isupper() and len(w) > 2 and w.lower() not in CONNECTOR for w in words)


YOUTH = re.compile(r"jovd|jonge |jongeren|cdja|perspectief|jonger", re.I)
FOREIGN = re.compile(r"buitenland|internationa|europese|europa|there|frei|matra", re.I)
SCIENCE = re.compile(r"wetenschappelijk|scientific|instituut|institute|wetenschappel|bureau|telders|wiardi|"
                     r"mierlo|bolkestein|groen van prinsterer|prof\.|academie", re.I)


def soort(name: str, context: str) -> str:
    """Judge by the entity's own name first; context only when the name is silent.

    The context window spans several lines and mentions sibling entities, so letting it decide labels the
    scientific institute 'jongeren' whenever the youth organisation appears next to it.
    """
    for source in (name, context):
        if YOUTH.search(source):
            return "jongeren"
        if FOREIGN.search(source):
            return "buitenland"
        if SCIENCE.search(source):
            return "wetenschappelijk"
    return "overig"


def to_eur(s: str) -> str:
    s = s.strip().replace("€", "").replace(" ", "")
    if re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+", s):
        # '1,843' in a Dutch report is one thousand eight hundred, not a euro and 843 cents
        s = s.replace(",", "")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(".", "")
    try:
        v = float(s)
    except ValueError:
        return ""
    return f"{v:.2f}" if v else ""


def parse(path: Path) -> list[dict]:
    year = path.name[:4]
    raw_party = path.name[5:].rsplit("_", 2)[0]
    partij = PARTY_CANON.get(raw_party, raw_party)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows: dict[str, dict] = {}

    def add(raw_name: str, amount: str, quote: str, ctx: str) -> None:
        name = re.sub(r"\s+", " ", ARTICLE.sub("", raw_name.strip(" .;:,"))).strip()
        # A row can carry two figures (budget and actual). Strip them all; use the last only if it is alone,
        # because between 363.799 and 351.705 nothing in the line says which is which, and guessing would be
        # inventing a number.
        stripped: list[str] = []
        while True:
            m = TRAILING_NUMBER.match(name)
            if not m:
                break
            stripped.append(m.group(2))
            name = m.group(1).strip()
        if not amount and len(stripped) == 1:
            amount = to_eur(stripped[0])
        name = re.sub(r"\s+", " ", LIST_MARKER.sub("", name))
        name = LEDGER_LABEL.sub("", name).strip(" .;:,•·")
        if not ENTITY_HINT.search(name) or NOT_A_NAME.match(name) or not looks_like_name(name):
            return
        key = name.lower()
        prev = rows.get(key)
        if prev is None:
            rows[key] = {
                "partij": partij, "jaar": year, "entiteit": name,
                "soort": soort(name, ctx), "bedrag_eur": amount,
                "evidence_quote": quote[:200], "bron_bestand": path.name,
            }
        elif not prev["bedrag_eur"] and amount:
            prev["bedrag_eur"] = amount

    for i, line in enumerate(lines):
        low = line.lower()
        if "neveninstelling" not in low and "per entiteit" not in low:
            continue
        ctx = " ".join(lines[max(0, i - 2): i + 2])
        for j in range(i + 1, min(i + 22, len(lines))):
            cand = lines[j]
            if not cand.strip():
                continue
            if re.search(r"(hoogachtend|controleverklaring|ondertekening|pagina\s+\d)", cand, re.I):
                break
            m = TABLEROW.match(cand)
            if m:
                add(m.group(1), to_eur(m.group(2)), cand.strip(), ctx)
                continue
            m = BULLET.match(cand)
            if m:
                add(m.group(1), "", cand.strip(), ctx)
                continue
            if ENTITY_HINT.search(cand) and looks_like_name(cand.strip()):
                add(cand.strip(), "", cand.strip(), ctx)
    return list(rows.values())


def main() -> int:
    files = sorted(TEXT.glob("*.txt"))
    if not files:
        print("no corpus; run scripts/fetch_corpus.sh first", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for f in files:
        rows.extend(parse(f))
    rows.sort(key=lambda r: (r["partij"], r["jaar"], r["entiteit"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    per_year = Counter(r["jaar"] for r in rows)
    per_year_amt = Counter(r["jaar"] for r in rows if r["bedrag_eur"])
    parties = {r["partij"] for r in rows}
    all_parties = {PARTY_CANON.get(f.name[5:].rsplit("_", 2)[0], f.name[5:].rsplit("_", 2)[0]) for f in files}

    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    print(f"rows={len(rows)}  distinct entities={len({r['entiteit'].lower() for r in rows})}  "
          f"with amount={sum(1 for r in rows if r['bedrag_eur'])}")
    print("rows per year:", dict(sorted(per_year.items())))
    print("of which with an amount:", dict(sorted(per_year_amt.items())))
    print(f"parties naming at least one entity: {len(parties)}/{len(all_parties)}")
    print("parties naming nothing:", sorted(all_parties - parties))
    print("\nsample:")
    for r in rows[:10]:
        print(f"  {r['partij']:<7}{r['jaar']} {r['soort']:<16}{r['bedrag_eur'] or '-':>12}  {r['entiteit'][:58]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
