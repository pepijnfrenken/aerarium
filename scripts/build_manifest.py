#!/usr/bin/env python3
"""Generate docs/MANIFEST.md: every artifact in out/, the script that builds it, or a curated label.

Two audits found artifacts with no producer and a reader who cannot rebuild a file cannot check it.
This walks out/, searches scripts/ and src/ for the filename, and writes the mapping. Anything with
no producer must be declared CURATED with a reason, or this exits non-zero.

The distinction matters because once a hand-built table sits beside computed ones, nobody can tell
which rows carry a document behind them and which carry a judgement. Curated is not a defect; an
*unlabelled* curated file is.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CODE_DIRS = [ROOT / "scripts", ROOT / "src"]

# Files that are inputs, not products. Each needs a reason, and the reason is the point.
CURATED: dict[str, str] = {
    "party-lineage.json": (
        "Hand-entered party lineage: one dated event per name change, merger or split, each with a source URL. "
        "No public register states when a party stopped existing; the statute and the party's own announcements do."
    ),
    "neveninstellingen-functie.json": (
        "Hand-coded function, type and certainty for each ancillary entity, each with a source URL or an explicit "
        "'from_name' basis. Registers publish names and amounts, never what an entity does."
    ),
    "seats.json": (
        "Kiesraad seat allocation, transcribed per election. The seat builder serialises curated figures rather "
        "than parsing a machine-readable source, because the published result files are PDFs."
    ),
    "index.html": (
        "The reader-facing page shell: hand-written markup, CSS and browser code. Only the embedded JSON payload "
        "is generated (by export_view.py, then reembed_view.py). The shell has no generator, which is why the "
        "render-layer bugs the audits found live here and are guarded by string assertions in verify_bindings.py."
    ),
}

# Artifacts produced indirectly: named inside another script or built by a two-step process.
INDIRECT: dict[str, str] = {
    "view-data.json": "scripts/export_view.py",
    "rekenkamer.json": "scripts/classify_rekenkamer.py --titles (or the full text pass, scripts/classify_rekenkamer.py)",
    "donor-typology.json": "scripts/classify_donors.py (then scripts/reembed_view.py)",
    "party-line-disclosure.csv": "src/aerarium/cli.py `aer grade`",
}


WRITE_TOKENS = re.compile(
    r"write_text|json\.dump|to_csv|DictWriter|open\([^)]*[\"']w[\"']|\.write\(|csv\.writer",
)
READ_TOKENS = re.compile(r"read_text|json\.load|DictReader|open\([^)]*[\"']r[\"']|read_csv|\.read\(")


def classify(name: str) -> tuple[list[str], list[str]]:
    """Split matches into files that WRITE the artifact and files that merely read it.

    Most scripts here point a module constant at the output path (`OUT = ROOT / "out" / "x.json"`)
    and write through it later, so the write call and the filename are not adjacent. Two cases:
    a write token near the mention, or a named constant that this same file later writes through.
    """
    writers: list[str] = []
    readers: list[str] = []
    needle = re.compile(re.escape(name))
    assign = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^\n]*$")
    for d in CODE_DIRS:
        for f in d.rglob("*.py"):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = str(f.relative_to(ROOT))
            role = None
            for m in needle.finditer(text):
                line_start = text.rfind("\n", 0, m.start()) + 1
                line = text[line_start: text.find("\n", m.end())]
                window = text[m.start(): m.start() + 200]
                a = assign.search(line)
                if a:
                    var = a.group(1)
                    if re.search(rf"\b{re.escape(var)}\s*\.write_text", text) or \
                       re.search(rf"write\w*\(\s*{re.escape(var)}\b", text) or \
                       re.search(rf"open\(\s*{re.escape(var)}\b[^)]*[\"']w[\"']", text) or \
                       re.search(rf"\b{re.escape(var)}\s*\.open\(\s*[\"']w", text) or \
                       re.search(rf"\b{re.escape(var)}\b[^\n]*DictWriter", text):
                        role = "w"
                        break
                if WRITE_TOKENS.search(window) or WRITE_TOKENS.search(line):
                    role = "w"
                    break
                role = role or "r"
            if role == "w":
                writers.append(rel)
            elif role == "r":
                readers.append(rel)
    return sorted(set(writers)), sorted(set(readers))


def main() -> int:
    if not OUT.exists():
        print("out/ does not exist", file=sys.stderr)
        return 1
    artifacts = sorted(p.name for p in OUT.iterdir() if p.is_file())
    rows: list[tuple[str, str, str]] = []
    orphans: list[str] = []

    for name in artifacts:
        if name in CURATED:
            rows.append((name, "CURATED", CURATED[name]))
            continue
        if name in INDIRECT:
            rows.append((name, INDIRECT[name], "produced in a step or via the CLI"))
            continue
        writers, readers = classify(name)
        note = f"read by {', '.join(readers)}" if readers else ""
        if writers:
            rows.append((name, ", ".join(writers), note))
        else:
            orphans.append(name)
            rows.append((name, "NO PRODUCER FOUND", note))

    lines = [
        "# Artifact manifest",
        "",
        "Generated by `scripts/build_manifest.py`. Every file in `out/` is listed with the code that",
        "builds it. A file with no producer must be declared CURATED in the script, with a reason; an",
        "unlabelled hand-made artifact is a failure of this build, not a style issue, because a reader",
        "who cannot rebuild a file cannot check it.",
        "",
        "| artifact | built by | note |",
        "|---|---|---|",
    ]
    for name, by, note in rows:
        lines.append(f"| `{name}` | {by} | {note} |")
    lines += [
        "",
        f"{len(rows)} artifacts: {sum(1 for _, b, _ in rows if b == 'CURATED')} curated, "
        f"{len(rows) - sum(1 for _, b, _ in rows if b == 'CURATED')} generated.",
        "",
        "## Rebuild order",
        "",
        "Run in this order; later steps read earlier outputs, and the embedded page payload is last:",
        "",
        "1. `scripts/fetch_*.sh` — refresh raw downloads into `data/raw/` (gitignored)",
        "2. `scripts/ingest_*.py` — load the store and emit the CSV/JSON extracts",
        "3. `scripts/export_view.py` — assemble `out/view-data.json` (FIRST pass: classify_donors reads it)",
        "4. `scripts/classify_donors.py`, `scripts/gift_timing.py`, `scripts/classify_creditors.py` — derived tables",
        "5. `scripts/export_view.py` — assemble it again, now with the derived tables in place",
        "6. `scripts/reembed_view.py` — inject the payload into `out/index.html`",
        "7. `scripts/verify_bindings.py` — bind prose to artifacts; must exit 0, then `--canary` must trip",
        "",
    ]
    (ROOT / "docs" / "MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote docs/MANIFEST.md: {len(rows)} artifacts")
    for name, by, _ in rows:
        if by == "NO PRODUCER FOUND":
            print(f"  NO PRODUCER: {name}")
    if orphans:
        print(f"\n{len(orphans)} artifact(s) have no producer and no CURATED declaration:")
        for o in orphans:
            print("  -", o)
        return 1
    print("every artifact is either generated or declared curated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
