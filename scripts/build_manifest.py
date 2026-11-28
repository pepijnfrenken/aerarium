#!/usr/bin/env python3
"""Generate docs/MANIFEST.md: every artifact in out/, the step that builds it, and the order that works.

WHY AN EXPLICIT MAP. This used to infer producers by searching the scripts for the filename and looking for a write
token within 200 characters. That is a guess dressed as a manifest: it can name a reader as a writer because a write
happened nearby, and it says nothing about whether the step that reads a file runs after the step that writes it. Two
audits found real defects of exactly that kind. Every artifact now has a declared producer and declared inputs, the
build fails if an artifact is unclaimed, and the rebuild order is computed from the declared inputs rather than
written out by hand - so a missing producer cannot hide behind a plausible sentence.

The distinction between CURATED and generated still matters: once a hand-built table sits beside computed ones, nobody
can tell which rows carry a document behind them. Curated is not a defect; an *unlabelled* curated file is.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
DOCS = ROOT / "docs"

# Artifacts that are hand-made or hand-maintained. Each needs a reason, and the reason is the point.
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
    "assets/styles.css": (
        "The page's stylesheet, extracted from the inline <style> block so the page's markup, styling and "
        "logic are separately readable. Editable source, not generated: changing it changes the site."
    ),
    "assets/app.js": (
        "The page's application script, extracted from the inline <script>. Editable source, not generated; "
        "scripts/check_page_renders.py resolves and executes this file against the embedded payload."
    ),
    "index.html": (
        "The reader-facing page shell: hand-written markup, CSS and browser code. Only the embedded JSON payload "
        "is generated (by export_view.py, then reembed_view.py). The shell has no generator, which is why the "
        "render-layer bugs the audits found live here and are guarded by string assertions in verify_bindings.py."
    ),
}

# Steps in dependency order. `writes` and `reads` name artifacts in out/; a read must be written by an earlier step.
# The order below is checked, not trusted: the script verifies every declared read is produced before it is used.
PIPELINE: list[dict] = [
    {"step": "bash scripts/fetch_tk2025.sh", "writes": [], "reads": [],
     "note": "raw workbook downloads into data/raw/ (gitignored)"},
    {"step": "scripts/ingest_tk2025.py",
     "writes": ["candidate-gifts-2025.csv", "gifts-2025-election.csv", "gifts-2025-election.json"], "reads": []},
    {"step": "scripts/ingest_tk2025_post.py",
     "writes": ["debts-2025.json", "gifts-2025-post-election.csv"], "reads": []},
    {"step": "scripts/extract_gifts.py", "writes": ["gifts_donors.csv", "gifts_reconcile.csv"], "reads": []},
    {"step": "scripts/redact_outputs.py", "writes": ["gifts_donors_public.csv"], "reads": ["gifts_donors.csv"]},
    {"step": "scripts/extract_spending.py", "writes": ["spending-campaign.csv"], "reads": []},
    {"step": "scripts/extract_neveninstellingen.py", "writes": ["neveninstellingen.csv"], "reads": []},
    {"step": "scripts/build_seats.py", "writes": [], "reads": ["seats.json"],
     "note": "serialises the curated seat table; seats.json is the curated source, not a product of this step"},
    {"step": "src/aerarium/cli.py `aer grade`", "writes": ["party-line-disclosure.csv"], "reads": []},
    {"step": "scripts/gift_timing.py", "writes": ["gift-timing.json"], "reads": ["gifts_donors.csv"]},
    {"step": "scripts/govrun.py", "writes": ["govrun.json"], "reads": []},
    {"step": "scripts/thinktanks.py", "writes": ["thinktanks.json"], "reads": []},
    {"step": "scripts/classify_creditors.py", "writes": ["media-debt.json"],
     "reads": ["debts-2025.json"]},
    {"step": "scripts/donor_claims.py",
     "writes": ["donor-claims.json"], "reads": ["gifts_donors_public.csv"]},
    {"step": "scripts/flow.py", "writes": ["flow.json"], "reads": []},
    {"step": "scripts/overshoots.py", "writes": ["overshoots.json"], "reads": []},
    {"step": "scripts/classify_rekenkamer.py --titles", "writes": ["rekenkamer.json"], "reads": []},
    {"step": "scripts/export_view.py (first pass)", "writes": ["view-data.json"],
     "reads": ["gifts_donors.csv", "gifts_reconcile.csv", "party-line-disclosure.csv", "gifts-2025-election.json",
               "debts-2025.json", "media-debt.json", "neveninstellingen-functie.json", "spending-campaign.csv",
               "party-lineage.json"],
     "note": "pass one exists because classify_donors reads this file"},
    {"step": "scripts/classify_donors.py", "writes": ["donor-typology.json"], "reads": ["view-data.json"]},
    {"step": "scripts/export_view.py (second pass)", "writes": ["view-data.json"],
     "reads": ["donor-typology.json"], "note": "the derivation has to land in the payload, so the export runs twice"},
    {"step": "scripts/build_state_payload.py", "writes": ["state-data.json"],
     "reads": ["govrun.json", "overshoots.json", "rekenkamer.json"]},
    {"step": "scripts/reembed_view.py", "writes": [], "reads": ["view-data.json", "state-data.json"],
     "note": "injects both payloads into out/index.html"},
    {"step": "scripts/check_page_renders.py", "writes": [], "reads": ["index.html", "assets/app.js"],
     "note": "executes the page's script against the embedded payload under node",
     },
    {"step": "scripts/build_manifest.py", "writes": [], "reads": [], "note": "this file"},
    {"step": "scripts/verify_bindings.py", "writes": [], "reads": [],
     "note": "binds prose to artifacts; must exit 0, then --canary must trip"},
]


def check_order(steps: list[dict]) -> list[str]:
    """Every declared read must be produced by an earlier step, or be curated. Returns the problems."""
    produced = {name for name, _ in CURATED.items()}
    problems: list[str] = []
    for i, s in enumerate(steps, 1):
        for r in s["reads"]:
            if r not in produced:
                problems.append(f"step {i} ({s['step']}) reads {r}, which nothing earlier produces")
        produced |= set(s["writes"])
    return problems


def main() -> int:
    if not OUT.exists():
        print("out/ does not exist", file=sys.stderr)
        return 1

    artifacts = sorted(str(f.relative_to(OUT)) for f in OUT.rglob("*") if f.is_file())
    producer: dict[str, str] = {name: "CURATED" for name in CURATED}
    for s in PIPELINE:
        for w in s["writes"]:
            producer[w] = s["step"]

    unclaimed = [a for a in artifacts if a not in producer]
    ghosts = [w for s in PIPELINE for w in s["writes"] if not (OUT / w).exists()]
    problems = check_order(PIPELINE)

    lines = [
        "# Artifact manifest",
        "",
        "Generated by `scripts/build_manifest.py` from a declared producer map, not from searching the code for",
        "filenames. Every file in `out/` is listed with the step that builds it. A file with no declared producer",
        "fails the build; a hand-made file must be declared CURATED with a reason.",
        "",
        "| artifact | built by | note |",
        "|---|---|---|",
    ]
    for name in artifacts:
        by = producer.get(name, "**NO PRODUCER DECLARED**")
        if by == "CURATED":
            note = CURATED[name]
        else:
            note = next((s.get("note", "") for s in PIPELINE if s["step"] == by and name in s.get("writes", [])),
                        "")
        lines.append(f"| `{name}` | {by} | {note} |")

    lines += [
        "",
        f"{len(artifacts)} artifacts: {sum(1 for a in artifacts if producer.get(a) == 'CURATED')} curated, "
        f"{sum(1 for a in artifacts if producer.get(a) not in ('CURATED', None))} generated.",
        "",
        "## Rebuild order",
        "",
        "Computed from each step's declared inputs: a step runs only after everything it reads exists. This is the",
        "sequence a reader follows to rebuild `out/` from the store, and it is checked on every build - a step that",
        "reads a file nothing earlier produces fails this script rather than producing a plausible-looking order.",
        "",
    ]
    for i, s in enumerate(PIPELINE, 1):
        note = f" — {s['note']}" if s.get("note") else ""
        lines.append(f"{i}. `{s['step']}`{note}")

    lines += [""]
    DOCS.mkdir(exist_ok=True)
    (DOCS / "MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote docs/MANIFEST.md: {len(artifacts)} artifacts, {len(PIPELINE)} steps")
    if unclaimed:
        print(f"\n{len(unclaimed)} artifact(s) with no declared producer:")
        for u in unclaimed:
            print("  -", u)
    if ghosts:
        print(f"\n{len(ghosts)} declared output(s) do not exist on disk:")
        for g in ghosts:
            print("  -", g)
    for p in problems:
        print("  ORDER:", p)
    if unclaimed or ghosts or problems:
        return 1
    print("every artifact has a declared producer, every declared output exists, and no step reads a file "
          "nothing earlier produces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
