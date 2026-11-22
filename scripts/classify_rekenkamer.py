#!/usr/bin/env python3
"""Attach Rekenkamer publications to budget chapters, and grade how strong the attachment is.

Rung 6 of the chain is a finding on a line. The Rekenkamer publishes no machine-readable link between
a report and a begrotingsartikel (PROBE-008), so the join is document classification. This script does
the classification and, more importantly, refuses to overstate it:

  * the unit is a PUBLICATION, not a finding on an article;
  * attachment is to a CHAPTER, never to a beleidsartikel, because a report naming a ministry does not
    name article 3 of that ministry's chapter;
  * every attachment carries its strength: `title` when the publication's own title names the ministry,
    `body` when only the text does, and no attachment when neither does;
  * the false-positive rate is measurable, because a `title` match and a `body` match are different
    claims and are counted apart. A `body` match is a lead, not an attachment.

Text extraction is pdftotext (poppler). PDFs are disposable; the text and the JSON are the artifacts.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "rekenkamer"
TEXT = CORPUS / "text"
PDF_INDEX = CORPUS / "pdfs.json"
OUT = ROOT / "out" / "rekenkamer.json"

# Chapter -> the words a report would use for that ministry. Kept narrow on purpose: a broad term like
# "zorg" appears in almost every report about anything, and a match on it says nothing.
CHAPTER_TERMS = {
    "I": ["de koning", "koninklijk huis"],
    "III": ["algemene zaken", "ministerie van algemene zaken"],
    "IV": ["koninkrijksrelaties", "caribisch nederland", "bonaire", "sint eustatius", "saba"],
    "V": ["buitenlandse zaken", "ambassade", "consulaire"],
    "VI": ["justitie en veiligheid", "politie", "openbaar ministerie", "rechtspraak", "gevangenis"],
    "VII": ["binnenlandse zaken", "koninkrijksrelaties", "gemeenten", "provincies", "kiesraad"],
    "VIII": ["onderwijs, cultuur en wetenschap", "primair onderwijs", "voortgezet onderwijs",
             "middelbaar beroepsonderwijs", "hoger onderwijs", "cultureel", "media"],
    "IX": ["financiën", "belastingdienst", "rijksschuld", "staatsleningen", "douane"],
    "X": ["defensie", "krijgsmacht", "marine", "luchtmacht", "landmacht"],
    "XII": ["infrastructuur en waterstaat", "rijkswaterstaat", "rws", "spoor", "vaarwegen",
            "luchtvaart", "autoriteit woningcorporaties"],
    "XIII": ["economische zaken", "klimaatbeleid", "energiebeleid", "mededingingsautoriteit", "acm",
             "octrooicentrum"],
    "XIV": ["landbouw, natuur en voedselkwaliteit", "landbouw", "visserij", "voedselkwaliteit",
            "nvwa", "stikstof"],
    "XV": ["sociale zaken en werkgelegenheid", "uitkeringen", "werkloosheid", "arbeidsongeschiktheid",
           "bijstand", "kinderopvangtoeslag"],
    "XVI": ["volksgezondheid", "welzijn en sport", "zorgverzekeringsfonds", "nvwa", "ggd",
            "jeugdzorg"],
    "XVII": ["buitenlandse handel en ontwikkelingssamenwerking", "ontwikkelingssamenwerking", "os",
             "bhkos", "handel en ontwikkelingssamenwerking"],
    "XVIII": ["wonen en rijksdienst", "rijksdienst", "woningmarkt", "huurtoeslag"],
    "XIX": ["nationaal groeifonds"],
    "XX": ["asiel en migratie", "asiel", "immigratie", "ind"],
    "A": ["mobiliteitsfonds", "infrastructuurfonds"],
    "B": ["gemeentefonds"],
    "C": ["provinciefonds"],
    "F": ["diergezondheidsfonds"],
    "H": ["bes-fonds"],
}

PAGE_RE = re.compile(r"\s+")


def extract_text(pdf: Path) -> str:
    try:
        r = subprocess.run(["pdftotext", "-q", "-layout", str(pdf), "-"],
                           capture_output=True, timeout=180)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def count_term(text: str, term: str) -> int:
    # Word-boundary match on the normalised text: substring counting would make "zorg" match "zorgvuldig"
    # and inflate every attachment. Short terms are matched whole-word only.
    pat = r"(?<![a-z])" + re.escape(term) + r"(?![a-z])"
    return len(re.findall(pat, text))


def classify(title: str, text: str) -> list[dict]:
    low_title = (title or "").lower()
    low_text = text.lower()
    hits = []
    for chapter, terms in CHAPTER_TERMS.items():
        n_text = sum(count_term(low_text, t) for t in terms)
        n_title = sum(count_term(low_title, t) for t in terms)
        if not n_text and not n_title:
            continue
        hits.append({
            "chapter": chapter,
            "in_title": n_title,
            "in_body": n_text,
            "strength": "title" if n_title else "body",
        })
    hits.sort(key=lambda h: (h["in_title"], h["in_body"]), reverse=True)
    return hits


# A Rekenkamer publication is not always a finding. The register also carries the ministry's response to a
# finding, the ministry's answers to parliamentary questions about it, and covering briefs. Attaching a
# ministry's own reaction to a budget line as though it were an audit finding would invert the chain: the
# finding is the Rekenkamer's, the response is the auditee's.
KIND_RULES = [
    ("reactie", ("reactie ", "reactie van", "reactie minister")),
    ("beantwoording", ("beantwoording", "antwoord op vragen", "antwoorden op vragen")),
    ("brief", ("brief aan", "afschrift brief", "brief van")),
    ("bijlage", ("overzicht fouten en onzekerheden",)),
    ("aandachtspunten", ("aandachtspunten bij de ontwerpbegroting",)),
    ("verantwoordingsonderzoek", ("verantwoordingsonderzoek", "resultaten verantwoordingsonderzoek")),
]


def document_kind(title: str) -> str:
    low = (title or "").lower().strip()
    for kind, prefixes in KIND_RULES:
        if any(low.startswith(p) or p in low[:60] for p in prefixes):
            return kind
    return "overig"


def is_finding(kind: str) -> bool:
    """What counts as a Rekenkamer finding for rung 6: its own research, not a reaction to it."""
    return kind in ("verantwoordingsonderzoek", "aandachtspunten", "bijlage")


def load_jsonl(path: Path) -> list[dict]:
    """Local copy of the fetcher's loader: these scripts are run separately and share no package."""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def titles_only_mode() -> int:
    """Classify from titles alone, when PDF text is not available.

    This exists because the host blocked the crawler after 1.769 of 2.677 metadata pages. A title match is the
    strong rule, so it can be published on its own; the body rule cannot, and this mode records it as
    NOT ATTEMPTED rather than as a zero. Reporting `0 body matches` would be a false statement about the
    documents, since none of them were read.
    """
    pages = [r for r in load_jsonl(CORPUS / "pages.jsonl") if not r.get("error")]
    seen, docs = set(), []
    for rec in pages:
        if rec["url"] in seen:
            continue
        seen.add(rec["url"])
        hits = classify(rec.get("title") or "", "")
        docs.append({
            "title": rec.get("title"),
            "date": rec.get("date"),
            "jaar": rec.get("jaar"),
            "page": rec.get("url"),
            "pdf": (rec.get("pdfs") or [None])[0],
            "kind": document_kind(rec.get("title") or ""),
            "chapters_in_title": [h["chapter"] for h in hits if h["strength"] == "title"],
            "chapters_in_body_only": None,
            "hits": hits[:6],
            "top_chapter": hits[0]["chapter"] if hits else None,
            "top_strength": "title" if hits else None,
        })
    titled = [d for d in docs if d["chapters_in_title"]]
    by_chapter: dict[str, int] = {}
    for d in titled:
        for c in d["chapters_in_title"]:
            by_chapter[c] = by_chapter.get(c, 0) + 1
    payload = {
        "generated_by": "scripts/classify_rekenkamer.py --titles",
        "source": "rekenkamer.nl publications, harvested from the site's sitemap index",
        "licence": "no explicit licence stated on the publication pages; text used for classification only",
        "unit": "one publication (page), not one finding on an article",
        "mode": "titles-only",
        "coverage": {
            "pages_harvested": len(docs),
            "pages_in_scope": 2677,
            "harvest_complete": False,
            "why_incomplete": ("the host answered HTTP 403 to every request after roughly 1.400 pages at four "
                               "connections; the crawler stopped rather than retrying into the block"),
            "pdfs_downloaded": 0,
        },
        "rule": ("A chapter is attached when the publication's OWN TITLE names that ministry. No attachment is made "
                 "to a beleidsartikel: a report naming a ministry does not name article 3 of it."),
        "counts": {
            "publications_classified": len(docs),
            "attached_by_title": len(titled),
            "attached_by_title_and_a_finding": len([d for d in titled if is_finding(d["kind"])]),
            "body_matches_not_attempted": len(docs),
            "no_chapter_in_title": len(docs) - len(titled),
        },
        "by_kind": {k: sum(1 for d in docs if d["kind"] == k)
                    for k in sorted({d["kind"] for d in docs})},
        "by_chapter": dict(sorted(by_chapter.items(), key=lambda x: -x[1])),
        "caveat": ("Body text was NOT read: no PDF was downloaded before the block. The body-match count is "
                   "therefore not zero, it is unmeasured, and is reported as null rather than as a number. A "
                   "title match says the publication is about that ministry's domain; it does not say the "
                   "publication is a finding on any budget line."),
        "documents": docs,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} (titles-only, coverage incomplete)")
    for k, v in payload["counts"].items():
        print(f"  {k:<34}{v:>5}")
    print("  by chapter:", payload["by_chapter"])
    print("  by kind:", payload["by_kind"])
    return 0


def main() -> int:
    if "--titles" in sys.argv:
        return titles_only_mode()
    if not PDF_INDEX.exists():
        print(f"missing {PDF_INDEX}; run fetch_rekenkamer.py --pdfs first", file=sys.stderr)
        return 1
    index = json.loads(PDF_INDEX.read_text(encoding="utf-8"))
    TEXT.mkdir(parents=True, exist_ok=True)

    docs, unreadable, no_pdf = [], [], 0
    for url, rec in index.items():
        if rec.get("error") or not rec.get("file"):
            no_pdf += 1
            continue
        pdf = ROOT / rec["file"]
        if not pdf.exists():
            unreadable.append({"url": url, "why": "file missing on disk"})
            continue
        txt_path = TEXT / (pdf.stem + ".txt")
        if txt_path.exists():
            text = txt_path.read_text(encoding="utf-8", errors="replace")
        else:
            text = extract_text(pdf)
            txt_path.write_text(text, encoding="utf-8")
        if len(text.strip()) < 200:
            unreadable.append({"url": url, "why": f"only {len(text.strip())} chars of text (scan?)"})
            continue
        hits = classify(rec.get("title") or "", text)
        docs.append({
            "title": rec.get("title"),
            "date": rec.get("date"),
            "jaar": rec.get("jaar"),
            "page": rec.get("page"),
            "pdf": url,
            "text_chars": len(text),
            "chapters_in_title": [h["chapter"] for h in hits if h["strength"] == "title"],
            "chapters_in_body_only": [h["chapter"] for h in hits if h["strength"] == "body"],
            "hits": hits[:6],
            "top_chapter": hits[0]["chapter"] if hits else None,
            "top_strength": hits[0]["strength"] if hits else None,
        })

    titled = [d for d in docs if d["chapters_in_title"]]
    bodyonly = [d for d in docs if not d["chapters_in_title"] and d["chapters_in_body_only"]]
    unattached = [d for d in docs if not d["chapters_in_title"] and not d["chapters_in_body_only"]]

    payload = {
        "generated_by": "scripts/classify_rekenkamer.py",
        "source": "rekenkamer.nl publications, harvested from the site's sitemap index",
        "licence": "no explicit licence stated on the publication pages; text used for classification only, corpus not republished",
        "unit": "one publication (PDF), not one finding on an article",
        "rule": ("A chapter is attached when the publication's own text names that ministry; the strength says "
                 "whether the title alone carries it (strong) or only the body does (a lead). No attachment is "
                 "made to a beleidsartikel, because a report naming a ministry does not name article 3 of it."),
        "counts": {
            "publications_classified": len(docs),
            "attached_by_title": len(titled),
            "attached_by_body_only": len(bodyonly),
            "no_chapter_mentioned": len(unattached),
            "downloaded_but_unreadable": len(unreadable),
            "recorded_but_not_downloaded": no_pdf,
        },
        "caveat": ("A body-only match is a lead, not an attachment: the ministry can be mentioned in a list of "
                   "addressees or in a comparison and the report be about something else entirely. The two "
                   "counts are published apart so a reader can see how much of the join rests on the weak rule."),
        "documents": docs,
        "unreadable": unreadable,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"wrote {OUT.relative_to(ROOT)}")
    for k, v in payload["counts"].items():
        print(f"  {k:<32}{v:>5}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
