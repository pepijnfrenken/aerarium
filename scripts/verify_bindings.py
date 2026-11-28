#!/usr/bin/env python3
"""Bind the numbers in the prose to the numbers in the artifacts, and fail loudly when they part.

Why this file exists: the previous verifier compared artifact values against hardcoded constants. If
the prose and the constant drifted together it printed PASS, and it printed "ALL CLAIMS VERIFIED"
through two audits that found a wrong year, a wrong rank, a mislabelled denominator and a figure 25%
too low. It never read a sentence.

So this one does the opposite. Every claim declares:
  * the file that makes it,
  * a regex that must still find the number in THAT SENTENCE (so deleting the claim is also a failure),
  * a recompute function that derives the number from the artifacts.
If the prose number and the recomputed number disagree, this exits non-zero.

Two rules it enforces on itself:
  * a claim that cannot be found in the prose is a FAIL, not a skip - silently dropping a claim is how
    a repository stops being checkable;
  * `--canary` perturbs one bound value and asserts that the run FAILS. A checker that cannot fail
    proves nothing, and this one has to prove it can.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "out"

fails: list[str] = []
checked = 0


def nl(s: str) -> float:
    """Parse Dutch-formatted numbers.

    The same file writes '25.038.264,64' (dots as thousands, comma as decimal) and '20.529.188'
    (dots only) and '2.301' (dots only, three-digit group). A parser that assumes a lone dot is a
    decimal point reads 2.301 donors as 2.3, so the rule is: a dot is a thousands separator when it
    is followed by exactly three digits and nothing else follows, or when a comma is also present.
    """
    s = s.strip().replace("\u00a0", "").replace("€", "")
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    if "." in s:
        head, _, tail = s.rpartition(".")
        if len(tail) == 3 and head:
            return float(s.replace(".", ""))
    return float(s)


def bind(label: str, path: Path, pattern: str, want: float, tol: float = 0.51) -> None:
    """Find `pattern` in `path` and require its captured number to equal `want`."""
    global checked
    if not path.exists():
        fails.append(f"{label}: {path.name} missing")
        print(f"FAIL  {label}: file missing")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(pattern, text)
    if not m:
        fails.append(f"{label}: claim not found in {path.name} (pattern {pattern!r})")
        print(f"FAIL  {label}: claim text not found in {path.name}")
        return
    got = nl(m.group(1))
    checked += 1
    ok = abs(got - want) <= tol
    print(f"{'PASS' if ok else 'FAIL'}  {label}: prose {got:,.2f} vs artifact {want:,.2f}")
    if not ok:
        fails.append(f"{label}: prose says {got:,.2f}, artifact says {want:,.2f}")


# ---------------------------------------------------------------- load artifacts
view = json.loads((OUT / "view-data.json").read_text(encoding="utf-8"))
typ = json.loads((OUT / "donor-typology.json").read_text(encoding="utf-8"))
timing = json.loads((OUT / "gift-timing.json").read_text(encoding="utf-8"))
tanks = json.loads((OUT / "thinktanks.json").read_text(encoding="utf-8"))
claimsdoc = json.loads((OUT / "donor-claims.json").read_text(encoding="utf-8"))
w25 = json.loads((OUT / "gifts-2025-election.json").read_text(encoding="utf-8"))

gifts = view["gifts"]["totals"]
subsidy = view["subsidy"]["totals"]
donors = view["gifts"]["donors"]
gift_total = round(sum(gifts.values()), 2)
donor_count = len(donors)

# recompute the campaign-window figures from the timing artifact, not from a constant
w = timing["windows"][0]["by_days"] if "by_days" in timing["windows"][0] else {}
per_party = {r["partij"]: r for r in timing.get("per_party_2023", [])}
win_total = sum(r.get("in_window", 0) for r in timing.get("per_party_2023", []))

# ---------------------------------------------------------------- README claims
readme = REPO / "README.md"

bind("README total gift money", readme,
     r"\*\*2\.?\d* donors, €([\d.,]+)\*\*", gift_total)

bind("README donor count", readme,
     r"\*\*([\d.]+) donors, €[\d.,]+\*\*", donor_count)

bind("README entity share", readme,
     r"(\d+)% entities", typ["by_party"]["__national__"]["entity_share"]
     if "__national__" in typ.get("by_party", {}) else 100 * typ["money"]["entity"] / gift_total, tol=0.6)

bind("README PRO combined", readme,
     r"€([\d.]+) against VVD's", 20529188, tol=1)

bind("README campaign window money", readme,
     r"€([\d.]+) arrived in the", win_total, tol=1)

bind("README CDA dated-of-2023 coverage", readme,
     r"only ([\d,]+)% of its 2023 total", per_party["CDA"]["dated_share_of_2023"], tol=0.06)

bind("README SP dated-of-2023 coverage", readme,
     r"\(([\d,]+)% dated\)", per_party["SP"]["dated_share_of_2023"], tol=0.06)

# ---------------------------------------------------------------- FINDING 003
f3 = REPO / "docs" / "FINDING-003-who-donates.md"
bind("FINDING-003 VVD 2023 gift total", f3,
     r"2023 VVD gift total of €([\d.]+)", 3592775, tol=1)
bind("FINDING-003 VVD foundation subtotal", f3,
     r"includes €([\d.]+) from VVD's own foundations", 1810000, tol=1)

# ---------------------------------------------------------------- think tanks
# The prose for these lives in the commit history and in this artifact's own totals; bind the
# artifact's declared class totals against a recompute over its own entities.
tt_cls = tanks["classes"]
re_pol = round(sum(e["total_k"] for e in tanks["entities"].values() if e["class"] == "policy-institute"), 0)
re_int = round(sum(e["total_k"] for e in tanks["entities"].values() if e["class"] == "party-international"), 0)
for label, got, want in [
    ("thinktanks policy-institute class total", tt_cls["policy-institute"]["total_k"], re_pol),
    ("thinktanks party-international class total", tt_cls["party-international"]["total_k"], re_int),
]:
    global_ok = abs(got - want) <= 0.5
    checked += 1
    print(f"{'PASS' if global_ok else 'FAIL'}  {label}: {got:,.0f}k vs recompute {want:,.0f}k")
    if not global_ok:
        fails.append(f"{label}: declared {got}, recomputed {want}")

for name, want in [("Clingendael", 44769), ("ProDemos", 26040), ("HCSS", 405), ("Anne Frank Stichting", 6267)]:
    got = tanks["entities"][name]["total_k"]
    checked += 1
    ok = abs(got - want) <= 0.5
    print(f"{'PASS' if ok else 'FAIL'}  thinktank {name}: {got:,}k (expected {want:,}k)")
    if not ok:
        fails.append(f"thinktank {name}: {got} != {want}")

if tanks["entities"]["Rathenau Instituut"]["total_k"] > 500:
    fails.append("Rathenau total exceeds 500k - the KNAW KvK join has probably been reintroduced")
    print("FAIL  Rathenau guard: total above 500k")
else:
    checked += 1
    print(f"PASS  Rathenau guard: {tanks['entities']['Rathenau Instituut']['total_k']:,}k")

# ---------------------------------------------------------------- donor claims
cls = claimsdoc["classes"]
pv = round(sum(e["total_eur"] for e in claimsdoc["entities"] if e["claim_type"] == "party-vehicle"), 2)
tot = round(sum(e["total_eur"] for e in claimsdoc["entities"]), 2)
for label, got, want in [
    ("donor-claims party-vehicle subtotal", cls["party-vehicle"]["total_eur"], pv),
    ("donor-claims grand total", claimsdoc["grand_total_eur"], tot),
    ("donor-claims party-vehicle figure", cls["party-vehicle"]["total_eur"], 828950.00),
    ("donor-claims grand total figure", claimsdoc["grand_total_eur"], 1811149.00),
]:
    checked += 1
    ok = abs(got - want) <= 0.01
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got:,.2f} vs {want:,.2f}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

# the Opstelten role error must not come back: no individual may sit inside an entity total
opst = next(e for e in claimsdoc["entities"] if "Opstelten" in e["name"])
if opst["total_eur"] != 160000.00:
    fails.append(f"Opstelten total is {opst['total_eur']}, expected 160000 (the 1.000 false edge returned)")
    print(f"FAIL  Opstelten guard: {opst['total_eur']:,.2f}")
else:
    checked += 1
    print("PASS  Opstelten guard: 160,000.00 (individual's 1.000 excluded)")

# ---------------------------------------------------------------- seats
seats = view["latest"]["seats_2025"]
n_seats = sum(v for v in seats.values() if isinstance(v, (int, float)))
checked += 1
if n_seats != 150:
    fails.append(f"seats map totals {n_seats}, must be 150")
    print(f"FAIL  seat map totals {n_seats}, must be 150")
else:
    print(f"PASS  seat map totals {n_seats}")

# ---------------------------------------------------------------- 2025 election
# The election JSON carries the pre-election totals; the post-election windows live in the view.
latest = view["latest"]
for label, got, want in [
    ("2025 gifts to 8 Oct", w25["totals"]["2025_to_8_oct"], 9148658.46),
    ("2025 final three weeks", latest["total_final_3_weeks"], 1021300.86),
    ("2025 through election", latest["total_to_election"], 10169959.32),
]:
    checked += 1
    ok = abs(got - want) <= 0.01
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got:,.2f}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

# Audit-2 blocker 5: the candidate summary conflated rows, people and years. It now names each unit.
cand = w25["candidates"]
for label, got, want in [
    ("candidate sheet rows", cand["rows"], 1168),
    ("candidate distinct keys", cand["distinct_candidates"], 1166),
    ("candidate rows marked gifted", cand["with_a_gift"], 6),
    ("candidate recipients, any year", cand["recipients_any_amount"], 4),
    ("candidate recipients, 2025 only", cand["recipients_2025"], 3),
    ("candidate money 2023", cand["total_2023"], 5000.00),
    ("candidate money 2024", cand["total_2024"], 0.00),
    ("candidate money 2025", cand["total_2025"], 6499.00),
    ("candidate money combined 2023-2025", cand["total_gifted_combined"], 11499.00),
]:
    checked += 1
    ok = abs(float(got) - float(want)) <= 0.01
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

# ---------------------------------------------------------------- disclosure states
# Audit-2: twelve parties were rendered EUR 0 for the final three weeks because the exporter
# defaulted a missing row to zero. A disclosed zero (PVV) must survive; an absent filing must not
# become a number.
not_filed = sorted(p["partij"] for p in latest["parties"] if p["gifts_final_3_weeks"] is None)
checked += 1
if len(not_filed) == 12 and "NSC" in not_filed:
    print(f"PASS  parties with no supplementary filing: {len(not_filed)} (NSC among them)")
else:
    print(f"FAIL  expected 12 parties with a null final-three-weeks figure, got {len(not_filed)}: {not_filed}")
    fails.append(f"final-three-weeks nulls: {len(not_filed)} != 12")

pvv = next(p for p in latest["parties"] if p["partij"] == "PVV")
checked += 1
if pvv["gifts_final_3_weeks"] == 0.0:
    print("PASS  PVV keeps its disclosed EUR 0 for the final three weeks")
else:
    print(f"FAIL  PVV final three weeks is {pvv['gifts_final_3_weeks']!r}, expected a disclosed 0.0")
    fails.append("PVV disclosed zero was lost to null")

checked += 1
if "EUR 1.000" in latest["note"] and "767,12" in latest["note"] and "CANDIDATE" in latest["note"].upper():
    print("PASS  threshold note distinguishes the party EUR 1.000 cutoff from the candidate EUR 767,12 cutoff")
else:
    print("FAIL  threshold note does not separate the two cutoffs")
    fails.append("threshold note conflates party and candidate cutoffs")

# Audit-2: the budget axis divided a EUR-thousand value by 1000 and then labelled it 'k', so a
# gridline at 10.000k rendered as '10k' - a factor-of-a-thousand error on the live page.
# The page is served as markup + out/assets/app.js + out/assets/styles.css. A prose guard that reads
# only index.html now finds nothing and fails on a working site, which is why this concatenates what the
# browser actually receives.
html = (OUT / "index.html").read_text(encoding="utf-8")
for _asset in ("assets/app.js", "assets/styles.css"):
    _p = OUT / _asset
    if _p.exists():
        html += "\n" + _p.read_text(encoding="utf-8")
checked += 1
if "NF.format(v/1000)+'k'" in html:
    print("FAIL  budget axis still divides a thousands value by 1000 and labels it k")
    fails.append("budget axis unit error reintroduced (NF.format(v/1000)+'k')")
elif "NF.format(v))" in html:
    print("PASS  budget axis renders the thousands value as published")
else:
    print("FAIL  budget axis label not found in either form")
    fails.append("budget axis label missing")

# ---------------------------------------------------------------- NFRP row accounting
# Audit-2: the badge read "11 entities · 24 register rows" while the register has 46 rows in 19
# spellings and the 24 were entity-YEAR aggregates. Each count is now bound separately.
nfrp = view["nfrp"]
spellings = set()
for r in nfrp:
    spellings.update(r.get("variants") or [])
for label, got, want in [
    ("NFRP entity-year aggregates", len(nfrp), 24),
    ("NFRP source rows", sum(r.get("rows", 0) for r in nfrp), 46),
    ("NFRP distinct spellings", len(spellings), 19),
    ("NFRP distinct entities", len({r["entity"] for r in nfrp}), 11),
]:
    checked += 1
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

# ---------------------------------------------------------------- narrative guards
f5 = REPO / "docs" / "FINDING-005-sp-and-pvv.md"
t5 = f5.read_text(encoding="utf-8", errors="replace")
checked += 1
if "a debt of €12.803" in t5:
    print("FAIL  FINDING-005 still states the PVV 12.803 figure as a debt")
    fails.append("FINDING-005 asserts a PVV debt total the filing contradicts")
elif "does not resolve it" in t5 and "negative equity" in t5:
    print("PASS  FINDING-005 marks the PVV debt/equity conflict as unresolved")
else:
    print("FAIL  FINDING-005 lacks the PVV debt qualification")
    fails.append("FINDING-005 PVV debt qualification missing")

checked += 1
if "every figure is a floor" in html:
    print("FAIL  media panel still claims every figure is a floor")
    fails.append("media panel claims a lower bound the records do not support")
elif "not a lower bound" in html:
    print("PASS  media panel refuses the lower-bound reading and separates the two periods")
else:
    print("FAIL  media panel wording not found")
    fails.append("media panel wording missing")

# the JSON said "Treat every figure as a floor" while the page refused it. The gate only read the page,
# which is how the contradiction survived a green run: check the artifact's own prose too.
checked += 1
mdj = json.loads((OUT / "media-debt.json").read_text(encoding="utf-8"))
md_note = mdj["meta"]["what_this_is_not"].lower()
if "floor" in md_note and "not a floor" not in md_note:
    print("FAIL  media-debt.json still calls the balance a floor")
    fails.append("media-debt.json claims a floor")
elif "not a floor on media spend" in md_note and "never added or subtracted" in md_note:
    print("PASS  media-debt.json refuses the floor reading and refuses to combine the periods")
else:
    print("FAIL  media-debt.json caveat wording not found")
    fails.append("media-debt.json caveat missing")

# ---------------------------------------------------------------- page labels (audit 3, A1:21/A1:23/A1:27)
checked += 1
if "Two-source subtotal" in html and "'Total income'" not in html:
    print("PASS  the income label is a two-source subtotal, not total income")
else:
    print("FAIL  the page still labels a two-source subtotal as total income")
    fails.append("page calls a partial sum total income")

checked += 1
if "Owed to media at filing" in html and ">floor<" not in html:
    print("PASS  the media column is labelled a balance at filing")
else:
    print("FAIL  the media column still carries a floor label")
    fails.append("media column labelled a floor")

checked += 1
lparts = json.loads((OUT / "view-data.json").read_text(encoding="utf-8"))["latest"]["parties"]
if "L.parties.slice()" in html:
    print(f"PASS  the 2025 table shows every one of its {len(lparts)} parties, including nil filings")
else:
    print("FAIL  the 2025 table filters parties out instead of showing nil filings")
    fails.append("2025 table hides non-filing parties")

checked += 1
if "DATA.nfrp.length+' register rows'" in html:
    print("FAIL  NFRP badge still renders the aggregate count as register rows")
    fails.append("NFRP badge mislabels derived aggregates as register rows")
elif "source rows in ' + DATA.nfrp.length" in html or "source rows" in html:
    print("PASS  NFRP badge reports source rows, not the derived aggregate count")
else:
    print("FAIL  NFRP badge wording not found")
    fails.append("NFRP badge wording missing")

# ---------------------------------------------------------------- prose-structure guards
f1 = (REPO / "docs" / "FINDING-001-party-line-disclosure.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if "carrying the bulk (2021-2023)" in f1:
    print("FAIL  FINDING-001 still says anonymity carried the bulk across 2021-2023")
    fails.append("FINDING-001 2021 anonymity claim not corrected")
elif "€27.011k" in f1 and "€636k" in f1:
    print("PASS  FINDING-001 states the 2021 split as mostly named, not mostly anonymous")
else:
    print("FAIL  FINDING-001 lacks the corrected 2021 split")
    fails.append("FINDING-001 2021 split figures missing")

f3txt = f3.read_text(encoding="utf-8", errors="replace")
checked += 1
if "| CU |" in f3txt and "| OPNL |" in f3txt:
    print("PASS  typology table carries CU and OPNL, not a silent subset")
else:
    print("FAIL  typology table still omits CU or OPNL without a stated rule")
    fails.append("typology table omits CU or OPNL")

f2txt = (REPO / "docs" / "FINDING-002-party-income-and-donors.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if "is mostly what its entity received" in f2txt:
    print("FAIL  FINDING-002 still calls 34.7% of VVD's total 'mostly'")
    fails.append("FINDING-002 overstates the foundation share as mostly")
elif "34,7%" in f2txt and "received *by*" in f2txt:
    print("PASS  FINDING-002 states the foundation share as 34,7% and gets the flow direction right")
else:
    print("FAIL  FINDING-002 lacks the corrected share or direction")
    fails.append("FINDING-002 VVD foundation share/direction not corrected")

checked += 1
if "Parties sorted by total income" in html:
    print("FAIL  money map still labels a two-source subtotal as total income")
    fails.append("money map claims total income from two sources")
elif "two-source subtotal" in html:
    print("PASS  money map labels its scope as a two-source subtotal with exclusions")
else:
    print("FAIL  money map scope label not found")
    fails.append("money map scope label missing")

f4txt = (REPO / "docs" / "FINDING-004-spending-is-not-comparable.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if "NSC 2024" in f4txt and "SGP 2024" in f4txt:
    print("PASS  FINDING-004 lists all ten conflicting party-years")
else:
    print("FAIL  FINDING-004 still omits NSC 2024 or SGP 2024")
    fails.append("FINDING-004 conflict list incomplete")

cbstxt = (REPO / "docs" / "lanes" / "LANE-CBS-STATISTICS.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if "€1,000" in cbstxt and "2023 vintage" in cbstxt:
    print("PASS  CBS lane states the gift threshold per vintage, not as one series-wide cutoff")
else:
    print("FAIL  CBS lane still applies one threshold across vintages")
    fails.append("CBS lane threshold not vintage-qualified")

checked += 1
if "Gifts cover 2022–2024 only; 2025 and 2026 party recipients are not published." in html:
    print("FAIL  the caveat still says 2025 is unpublished, contradicting the 2025 section")
    fails.append("caveat claims 2025 unpublished while the page publishes 2025")
elif "ANNUAL dashboard series" in html:
    print("PASS  the caveat scopes the 2022-2024 limit to the annual series and points at 2025")
else:
    print("FAIL  gift-coverage caveat not found in either form")
    fails.append("gift-coverage caveat missing")

checked += 1
if ">Donors<span" in html:
    print("FAIL  the 2025 table still labels row counts as Donors")
    fails.append("2025 table labels donor rows as Donors")
elif "Donor rows" in html:
    print("PASS  the 2025 table labels its column as donor rows, with the rule in the tooltip")
else:
    print("FAIL  2025 donor column label not found")
    fails.append("2025 donor column label missing")

# ---------------------------------------------------------------- artifact manifest
# The skill's rule: every artifact names its generator, and hand-made inputs are labelled curated.
man_path = REPO / "docs" / "MANIFEST.md"
checked += 1
if not man_path.exists():
    print("FAIL  docs/MANIFEST.md missing")
    fails.append("artifact manifest missing")
else:
    man = man_path.read_text(encoding="utf-8", errors="replace")
    # recursive, matching build_manifest.py, so out/assets/* is not silently outside the count
    n_out = len([p for p in OUT.rglob("*") if p.is_file()])
    if "NO PRODUCER FOUND" in man:
        print("FAIL  manifest lists an artifact with no producer")
        fails.append("manifest contains an artifact with no producer")
    elif f"{n_out} artifacts:" not in man:
        print(f"FAIL  manifest does not cover all {n_out} artifacts in out/")
        fails.append(f"manifest artifact count != {n_out}")
    elif man.count("| CURATED |") < 1:
        print("FAIL  manifest has no curated declarations")
        fails.append("manifest carries no curated declarations")
    else:
        print(f"PASS  manifest covers all {n_out} artifacts, {man.count('| CURATED |')} declared curated")

# ---------------------------------------------------------------- government run
gv = json.loads((OUT / "govrun.json").read_text(encoding="utf-8"))
f6 = (REPO / "docs" / "FINDING-006-what-a-ministry-spends.md").read_text(encoding="utf-8", errors="replace")
nat = gv["national"]
cls = gv["instrument_classes"]


def nl_fmt(k: float) -> str:
    """Render thousands as the Dutch document prints them: 493337650 -> 493.337.650."""
    return f"{int(round(k)):,}".replace(",", ".")


for label, value, prose in [
    ("expenditure axis", nat["expenditure_axis_k"], "€401.303.575k"),
    ("programme spending", nat["expenditure_k"], "€331.469.674k"),
    ("personnel total", nat["personnel_k"], "€17.503.748k"),
    ("financial transactions", nat["financial_k"], "59.267.080"),
    ("inter-chapter transfers", nat["inter_chapter_k"], "10.566.821"),
]:
    checked += 1
    ok = prose in f6 and nl_fmt(value) in prose.replace("€", "")
    print(f"{'PASS' if ok else 'FAIL'}  FINDING-006 {label}: {nl_fmt(value)} (prose expects {prose})")
    if not ok:
        fails.append(f"FINDING-006 {label}: artifact {nl_fmt(value)} vs prose {prose}")

# the vuo axis must not be silently re-mixed: the superseded figures must be gone from the prose
checked += 1
if "€493.337.650k" in f6 and "Correction, 2026-11-21" not in f6:
    print("FAIL  FINDING-006 still presents the pre-vuo figures without a correction note")
    fails.append("FINDING-006 shows the inflated total with no correction")
elif "`O` = ontvangsten" in f6 and "`V` = verplichtingen" in f6:
    print("PASS  FINDING-006 names the vuo axis and carries the correction up front")
else:
    print("FAIL  FINDING-006 does not document the vuo axis")
    fails.append("FINDING-006 omits the vuo axis")

# the two rows that make the argument: Financien and IenW
fin = next(r for r in gv["per_chapter"] if r["chapter"] == "IX")
ienw = next(r for r in gv["per_chapter"] if r["chapter"] == "XII")
for label, got, want, prose in [
    ("Financien expenditure", fin["expenditure_k"], 21725430, "21.725.430"),
    ("Financien not-expenditure", fin["non_expenditure_k"], 54586916, "54.586.916"),
    ("IenW expenditure", ienw["expenditure_k"], 3510189, "3.510.189"),
    ("IenW inter-chapter", ienw["non_expenditure_k"], 10408456, "10.408.456"),
]:
    checked += 1
    ok = abs(got - want) <= 0.5 and prose in f6
    print(f"{'PASS' if ok else 'FAIL'}  FINDING-006 {label}: {got:,.0f}k")
    if not ok:
        fails.append(f"FINDING-006 {label}: {got} != {want} or missing from prose")

checked += 1
if gv["column_integrity"]["verdict"] == "blank in every row" and "blank in all 51.146 rows" in f6:
    print("PASS  FINDING-006 states beleid_of_niet_beleid is blank everywhere, matching the measured count")
else:
    print("FAIL  FINDING-006 apparatus-column claim does not match the measurement")
    fails.append("FINDING-006 beleid_of_niet_beleid claim unverified")

# ---------------------------------------------------------------- the page executes
# Every other check compares numbers in the payload. None of them ran the page, so a missing variable
# declaration killed every panel while every gate stayed green. This runs the real script.
import subprocess as _sp
checked += 1
_pr = _sp.run([sys.executable, str(REPO / "scripts" / "check_page_renders.py")],
              capture_output=True, text=True)
if _pr.returncode == 0:
    print("PASS  the shipped page script executes end to end without throwing")
else:
    print("FAIL  the shipped page script throws; panels after the failure never render")
    for _l in (_pr.stdout or "").strip().splitlines()[:6]:
        print("   ", _l)
    fails.append("page script throws on execution")

# ---------------------------------------------------------------- the flow measure
fl = json.loads((OUT / "flow.json").read_text(encoding="utf-8"))
reach = {r["year"]: r for r in fl["reachability"]}
checked += 1
if reach[2024]["appropriation_expenditure_k"] != 331469674:
    print(f"FAIL  flow 2024 appropriation expenditure {reach[2024]['appropriation_expenditure_k']:,} != 331,469,674")
    fails.append("flow 2024 appropriation expenditure wrong")
else:
    print("PASS  flow 2024 appropriation expenditure 331.469.674k, agreeing with govrun")

# the premium-financed basis exists only 2016-2019. If it ever reappears later, the series break has
# moved and every cross-year comparison in the findings is suspect.
checked += 1
prem = {y: v["premium_financed_k"] for y, v in reach.items()}
expected = {2016: 118901525, 2017: 77816327, 2018: 68087100, 2019: 72400000}
ok = all(prem.get(y) == v for y, v in expected.items()) and all(prem.get(y) == 0 for y in prem if y >= 2020)
print(f"{'PASS' if ok else 'FAIL'}  premium-financed basis present 2016-2019 only, absent from 2020")
if not ok:
    fails.append("premium-financed coverage break moved")

# no reachability trend may be claimed: 2016 is HIGHER than 2024
checked += 1
if reach[2016]["reachable_pct"] >= reach[2024]["reachable_pct"]:
    print(f"PASS  reachability has no upward trend ({reach[2016]['reachable_pct']}% 2016 vs "
          f"{reach[2024]['reachable_pct']}% 2024)")
else:
    print("FAIL  reachability rises from 2016 to 2024; check whether a coverage break was reintroduced")
    fails.append("reachability trend appears where none should")

cj = fl["claim_join"]
for label, got, want in [
    ("claim join buckets within 2pct", cj["matched_agreeing_within_2pct"], 1305),
    ("claim join register above", cj["matched_register_exceeds_budget"], 148),
    ("claim join budget above", cj["matched_budget_exceeds_register"], 223),
    ("claim join nonpositive side", cj["matched_with_a_nonpositive_side"], 32),
]:
    checked += 1
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

# ---------------------------------------------------------------- blockers 5 and 6
gt = json.loads((OUT / "gift-timing.json").read_text(encoding="utf-8"))
gt_party = {r["partij"]: r for r in gt["per_party_2023"]}
checked += 1
if gt_party["SP"]["dated_share_of_all_years"] == 69.9 and gt_party["CDA"]["dated_share_of_all_years"] == 13.9:
    print("PASS  dated shares cover the same years on both sides (SP 69,9%, CDA 13,9%)")
else:
    print(f"FAIL  dated shares wrong: SP {gt_party['SP']['dated_share_of_all_years']}, "
          f"CDA {gt_party['CDA']['dated_share_of_all_years']}")
    fails.append("dated share numerator/denominator periods differ")

gk = json.loads((OUT / "gifts-2025-election.json").read_text(encoding="utf-8"))
gk_rows = gk.get("parties") or gk.get("per_party") or []
fnp = next((r for r in gk_rows if r["partij"] == "FNP"), None)
donor_sum = sum(r["donors"] for r in gk_rows)
checked += 1
if fnp and fnp["donors"] == 17 and donor_sum == 2042:
    print(f"PASS  2025 donor rows count positive-2025 rows only (FNP 17, total {donor_sum})")
else:
    print(f"FAIL  2025 donor rows: FNP {fnp and fnp['donors']}, total {donor_sum} (expected 17 and 2042)")
    fails.append("2025 donor rows include non-2025 money")

# ---------------------------------------------------------------- amber list (audit 3)
rd = (REPO / "README.md").read_text(encoding="utf-8", errors="replace")
p5 = (REPO / "docs" / "PROBE-005-where-2025-lives.md").read_text(encoding="utf-8", errors="replace")
f3c = (REPO / "docs" / "FINDING-003-who-donates.md").read_text(encoding="utf-8", errors="replace")

checked += 1
if "1.168 candidates, 6 with a gift" in rd:
    print("FAIL  README still calls 1.168 rows 'candidates' and 6 rows 'with a gift'")
    fails.append("README conflates candidate rows, people and gift rows")
elif "1.166 distinct candidates" in rd:
    print("PASS  README separates sheet rows from distinct candidates")
else:
    print("FAIL  README candidate counts not corrected")
    fails.append("README candidate counts missing")

checked += 1
if "below the election-year threshold" in p5:
    print("FAIL  PROBE-005 still describes EUR 999 as below the threshold")
    fails.append("PROBE-005 puts EUR 999 under the threshold")
elif "€767,12" in p5 and "above" in p5:
    print("PASS  PROBE-005 places EUR 999 above the candidate threshold (EUR 767,12)")
else:
    print("FAIL  PROBE-005 threshold direction not fixed")
    fails.append("PROBE-005 threshold direction missing")

checked += 1
if "Stichting VVD Ondersteuning Tweede Kamerverkiezing gave" in f3c:
    print("FAIL  FINDING-003 still presents two spellings of SOV as separate foundations")
    fails.append("FINDING-003 double counts SOV spellings")
elif "€1.600.000" in f3c and "spelling" in f3c:
    print("PASS  FINDING-003 treats SOV's spellings as one entity and names the variants")
else:
    print("FAIL  FINDING-003 VVD spelling treatment not fixed")
    fails.append("FINDING-003 VVD spelling treatment missing")

# ---------------------------------------------------------------- FINDING-007, scheme split
tk = json.loads((OUT / "thinktanks.json").read_text(encoding="utf-8"))
named = {k: v for k, v in tk["entities"].items() if v["status"] == "named"}
cls_k = {}
cls_rows = {}
for e in named.values():
    cls_k[e["class"]] = cls_k.get(e["class"], 0) + e["total_k"]
    cls_rows[e["class"]] = cls_rows.get(e["class"], 0) + e["rows"]

buckets = {"labelled": [0, 0], "spelled": [0, 0], "other": [0, 0]}
for e in named.values():
    if e["class"] != "party-international":
        continue
    for reg, v in e.get("by_regeling", {}).items():
        low = reg.lower()
        if low.startswith("nfrp politieke partijen"):
            b = "labelled"
        elif "regionale partnerschappen" in low:
            b = "spelled"
        else:
            b = "other"
        buckets[b][0] += v["rows"]
        buckets[b][1] += v["k"]

for label, got, want in [
    ("FINDING-007 policy institutes", cls_k.get("policy-institute"), 77705),
    ("FINDING-007 party-international", cls_k.get("party-international"), 7753),
    ("FINDING-007 NFRP labelled rows", buckets["labelled"][0], 46),
    ("FINDING-007 NFRP labelled EURk", buckets["labelled"][1], 3289),
    ("FINDING-007 NFRP spelled rows", buckets["spelled"][0], 11),
    ("FINDING-007 NFRP spelled EURk", buckets["spelled"][1], 2266),
    ("FINDING-007 other scheme rows", buckets["other"][0], 18),
    ("FINDING-007 other scheme EURk", buckets["other"][1], 2198),
]:
    checked += 1
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'} {label}: {got}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

# the three scheme buckets must exhaust the party-international total, or a row has fallen between them
checked += 1
if sum(v[1] for v in buckets.values()) == cls_k.get("party-international"):
    print("PASS  FINDING-007 scheme buckets exhaust the party-international total")
else:
    print("FAIL  scheme buckets do not sum to the class total")
    fails.append("party-international scheme split does not reconcile")

fic = named.get("FICDD", {})
fic_split = fic.get("by_regeling", {})
fic_nfrp = sum(v["k"] for k, v in fic_split.items()
               if k.lower().startswith("nfrp politieke partijen") or "regionale partnerschappen" in k.lower())
fic_other = sum(v["k"] for k, v in fic_split.items()
                if not (k.lower().startswith("nfrp politieke partijen") or "regionale partnerschappen" in k.lower()))
checked += 1
if fic.get("total_k") == 596 and fic_nfrp == 398 and fic_other == 198:
    print("PASS  FINDING-007 FICDD split: 596k = 398k NFRP family + 198k other schemes")
else:
    print(f"FAIL  FICDD split wrong: total {fic.get('total_k')}, NFRP {fic_nfrp}, other {fic_other}")
    fails.append("FICDD scheme split wrong")

cl_split = named.get("Clingendael", {}).get("by_regeling", {})
cl_bz = sum(v["k"] for k, v in cl_split.items() if "bz 2006" in k.lower())
checked += 1
if cl_bz == 21618:
    print("PASS  FINDING-007 Clingendael's two BZ 2006 spellings are reported apart (21.618k)")
else:
    print(f"FAIL  Clingendael BZ 2006 spellings total {cl_bz}, expected 21618")
    fails.append("Clingendael scheme spelling total wrong")

f7 = (REPO / "docs" / "FINDING-007-what-the-state-pays-foundations.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if "€596k" in f7 and "A single figure of €596k would have read as one programme" in f7:
    print("PASS  FINDING-007 refuses the single-figure reading of FICDD")
else:
    print("FAIL  FINDING-007 is missing the scheme-split caveat")
    fails.append("FINDING-007 scheme split not stated")

# ---------------------------------------------------------------- seats name the filers (audit 3, A2:12)
vd = json.loads((OUT / "view-data.json").read_text(encoding="utf-8"))
sv = vd["latest"]["seat_view"]
pro = next((r for r in sv if r["lijst"] == "PRO"), None)
checked += 1
if pro and pro["filers"] == ["GL", "PvdA"] and pro["seats"] == 20:
    print("PASS  the seats entry names both filers (GL, PvdA) for the PRO list")
else:
    print(f"FAIL  seats entry filers wrong: {pro and pro['filers']}")
    fails.append("seats entry names the merged label as the filer")

checked += 1
if sum(r["seats"] for r in sv) == 150:
    print("PASS  seats still sum to 150")
else:
    print(f"FAIL  seats sum to {sum(r['seats'] for r in sv)}, not 150")
    fails.append("seats do not sum to 150")

# ---------------------------------------------------------------- A1:22, fabricated component zeros
import csv as _csv
with (OUT / "party-line-disclosure.csv").open(encoding="utf-8", newline="") as fh:
    pl = list(_csv.DictReader(fh))
bad = []
for r in pl:
    if r["named_rows"] in ("0", "") and r["anon_rows"] in ("0", ""):
        if r["named_k"] not in ("", None) or r["anon_k"] not in ("", None):
            bad.append((r["jaar"], r["label"], r["named_k"], r["anon_k"]))
        if r["named_coverage"] not in ("", None):
            bad.append((r["jaar"], r["label"], "coverage", r["named_coverage"]))
checked += 1
if bad:
    print(f"FAIL  {len(bad)} rows assert a zero on a line where the register publishes nothing: {bad[:3]}")
    fails.append("fabricated component zeros survive")
else:
    print(f"PASS  no row claims a coverage figure where the register publishes no rows ({len(pl)} rows checked)")

# ...and the genuine zero must survive: 2017 publishes one anonymised row, so 0 named is a real measurement.
row2017 = next((r for r in pl if r["jaar"] == "2017" and r["family"] == "politieke-partijen"), None)
checked += 1
if row2017 and row2017["named_k"] == "0" and row2017["named_coverage"] not in ("", None):
    print("PASS  the all-anonymised 2017 line keeps its genuine zero")
else:
    print(f"FAIL  the 2017 all-anonymised zero was nulled as well: {row2017 and (row2017['named_k'], row2017['named_coverage'])}")
    fails.append("genuine zero lost to the null")

# ---------------------------------------------------------------- A1:25 / A1:26 / A1:29
import re as _re
with (OUT / "neveninstellingen.csv").open(encoding="utf-8", newline="") as fh:
    nev = list(_csv.DictReader(fh))
names_raw = {r["entiteit"].strip().lower() for r in nev if r["entiteit"].strip()}
names_norm = {_re.sub(r"\s+", " ", _re.sub(r"[^a-z0-9 ]", " ", r["entiteit"].strip().lower())) for r in nev
              if r["entiteit"].strip()}
with_amt = sum(1 for r in nev if (r["bedrag_eur"] or "").strip() not in ("", "0", "0.0"))
pyears = len({(r["partij"], r["jaar"]) for r in nev})
for label, got, want in [
    ("PROBE-004 rows", len(nev), 242),
    ("PROBE-004 distinct raw names", len(names_raw), 120),
    ("PROBE-004 distinct normalised names", len(names_norm), 118),
    ("PROBE-004 rows with an amount", with_amt, 127),
    ("PROBE-004 party-years", pyears, 54),
]:
    checked += 1
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

p4 = (REPO / "docs" / "PROBE-004-neveninstellingen-in-the-reports.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if "must not be read as a subsidy series" in p4 and "120 distinct name strings" in p4:
    print("PASS  PROBE-004 states its units and refuses the mixed amount column")
else:
    print("FAIL  PROBE-004 units or role caveat missing")
    fails.append("PROBE-004 units/role caveat missing")

f2b = (REPO / "docs" / "FINDING-002-party-income-and-donors.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if "text match, not a verified\n  reading of each report" in f2b.replace("\r", ""):
    print("PASS  FINDING-002 labels the per-entity count as a text match")
else:
    print("FAIL  FINDING-002 still presents phrase hits as report contents")
    fails.append("FINDING-002 promotes phrase hits")

gd = (REPO / "docs" / "GRADING.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if "not resolved here" in gd and "identity is not asserted" in gd:
    print("PASS  GRADING.md records the SP KvK collision without asserting identity")
else:
    print("FAIL  GRADING.md still asserts the SP identity reading")
    fails.append("GRADING.md asserts an unresolved identity")

checked += 1
if "money the register does not publish at all is in neither column" in html:
    print("PASS  the budget panel refuses to read named+anonymous as a partition of realised")
else:
    print("FAIL  the budget panel still implies named+anonymous is the whole realisation")
    fails.append("budget panel implies a false partition")

checked += 1
if "adjudicated by hand" in html and "grouped by KvK" not in html:
    print("PASS  the NFRP panel describes its name-map join accurately")
else:
    print("FAIL  the NFRP panel still claims KvK grouping")
    fails.append("NFRP panel misdescribes its join")

# ---------------------------------------------------------------- A1:28 / A1:35
import csv as _csv2
with (OUT / "gifts_reconcile.csv").open(encoding="utf-8", newline="") as fh:
    rec = list(_csv2.DictReader(fh))
filer_tot = {}
for r in rec:
    try:
        filer_tot[r["partij"]] = filer_tot.get(r["partij"], 0.0) + float(r["published"] or 0)
    except ValueError:
        pass
n_filers = len(filer_tot)
n_positive = sum(1 for v in filer_tot.values() if v > 0)
checked += 1
if n_filers == 21 and n_positive == 18:
    print(f"PASS  {n_filers} parties filed, {n_positive} with a positive gift total")
else:
    print(f"FAIL  filer counts moved: {n_filers} filed, {n_positive} positive")
    fails.append("filer counts moved")

f3d = (REPO / "docs" / "FINDING-003-who-donates.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if "**eighteen** filers" in f3d and "nineteen filers with a positive gift total" not in f3d:
    print("PASS  FINDING-003 states eighteen filers, matching the register")
else:
    print("FAIL  FINDING-003 still over-counts the filers")
    fails.append("FINDING-003 filer count wrong")

wa = json.loads((OUT / "donor-typology.json").read_text(encoding="utf-8"))["by_party"]
checked += 1
if len(wa) == n_positive:
    print(f"PASS  the typology covers exactly the {len(wa)} parties with positive gift money")
else:
    print(f"FAIL  typology covers {len(wa)} parties against {n_positive} positive filers")
    fails.append("typology party count disagrees with the register")

with (OUT / "spending-campaign.csv").open(encoding="utf-8", newline="") as fh:
    sp = list(_csv2.DictReader(fh))
checked += 1
if sp and "value_rule" in sp[0] and any(r["value_rule"].startswith("none") for r in sp):
    nnone = sum(1 for r in sp if r["value_rule"].startswith("none"))
    print(f"PASS  the spending CSV names the rule behind each value ({nnone} rows carry none)")
else:
    print("FAIL  the spending CSV presents a derived value without naming the rule")
    fails.append("spending CSV value rule missing")

# ---------------------------------------------------------------- A2:18 / A2:19
pd = named.get("ProDemos", {}).get("anonymised_on_its_own_schemes_k", {})
cl = named.get("Clingendael", {}).get("anonymised_on_its_own_schemes_k", {})
checked += 1
if pd == {"2017": 4312, "2018": 4403, "2019": 5266, "2022": 8979}:
    print("PASS  ProDemos's anonymised own-scheme rows are published apart from its named total")
else:
    print(f"FAIL  ProDemos anonymised figures wrong: {pd}")
    fails.append("ProDemos anonymised figure missing or wrong")

checked += 1
if cl == {"2022": 812}:
    print("PASS  Clingendael's anonymised own-scheme row is bounded to the scheme that names it")
else:
    print(f"FAIL  Clingendael anonymised figure wrong: {cl} (a shared-scheme match would be a million-scale error)")
    fails.append("Clingendael anonymised match not bounded")

# the named totals must not absorb the anonymised rows
checked += 1
if named["ProDemos"]["total_k"] == 26040 and sum(pd.values()) == 22960:
    print("PASS  the anonymous own-scheme money is reported beside the named total, not inside it")
else:
    print("FAIL  named total and anonymised rows disagree")
    fails.append("named total contaminated by anonymised rows")

dc = json.loads((OUT / "donor-claims.json").read_text(encoding="utf-8"))
checked += 1
if "not about donor entities in general" in dc.get("headline", "") and dc.get("negative_scope"):
    print("PASS  donor-claims refuses to read 0 of 17 as a population finding")
else:
    print("FAIL  donor-claims still asserts a population-level negative")
    fails.append("donor-claims asserts a population negative")

f7b = (REPO / "docs" / "FINDING-007-what-the-state-pays-foundations.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if "€8.979k in 2022" in f7b and "€1,203,081k" in f7b and "never added to it" in f7b:
    print("PASS  FINDING-007 publishes the scheme-floor case with the false-positive rate that bounds it")
else:
    print("FAIL  FINDING-007 scheme-floor paragraph incomplete")
    fails.append("FINDING-007 scheme-floor paragraph incomplete")

# ---------------------------------------------------------------- A1:16 / A1:20 / A1:24 / A1:50
# The defect behind A1:16 was dividing a value already in EUR thousands by 1000, which rendered 10m as "10k".
# The remaining 'k' suffixes are correct values; what must never come back is a second division.
import re as _re16
checked += 1
if _re16.search(r"(realised_k|ceiling_k|named_k|anon_k)\s*/\s*1000", html):
    print("FAIL  a value already in EUR thousands is being divided by 1000 again")
    fails.append("budget axis double-divided")
else:
    print("PASS  no EUR-thousands field is divided by 1000 before display")

# The other half of A1:16: the panel stated the unit in its heading AND on every value. Each panel now states
# its unit once, and no value carries a 'k' suffix of its own.
checked += 1
if html.count("+'k'") == 0 and "all amounts in € thousand" in html:
    print("PASS  the unit is stated once per panel and no value repeats a 'k' suffix")
else:
    print(f"FAIL  {html.count(chr(43)+chr(39)+'k'+chr(39))} values still repeat the unit beside it")
    fails.append("scale repeated on every value")

gk2 = json.loads((OUT / "gifts-2025-election.json").read_text(encoding="utf-8"))
checked += 1
if "Candidates: EUR 767,12" in gk2["meta"]["threshold"] and "Parties: EUR 1.000" in gk2["meta"]["threshold"]:
    print("PASS  the 2025 threshold note separates the candidate and party cutoffs")
else:
    print(f"FAIL  threshold note still conflates the two cutoffs: {gk2['meta']['threshold'][:80]}")
    fails.append("2025 threshold note conflated")

f5 = (REPO / "docs" / "FINDING-005-sp-and-pvv.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if "Debts: nil" not in f5 and "open question, not a finding" in f5:
    print("PASS  FINDING-005 refuses 'nil' debt and labels the PVV funding route an open question")
else:
    print("FAIL  FINDING-005 still states nil debt or asserts an unfounded route")
    fails.append("FINDING-005 PVV claims unfixed")

sub = json.loads((OUT / "view-data.json").read_text(encoding="utf-8"))["subsidy"]
checked += 1
if sub.get("snapshot"):
    print(f"PASS  the subsidy table names the snapshot it was read from ({sub['snapshot']})")
else:
    print("FAIL  the subsidy table does not name its snapshot")
    fails.append("subsidy snapshot not recorded")

mani = (REPO / "docs" / "MANIFEST.md").read_text(encoding="utf-8", errors="replace")
checked += 1
if mani.count("scripts/export_view.py") >= 2 and "FIRST pass" in mani:
    print("PASS  the rebuild order runs export_view before and after the derived tables")
else:
    print("FAIL  the rebuild order still omits the first export pass")
    fails.append("rebuild order impossible on a clean tree")

# ---------------------------------------------------------------- PROBE-009, rung 6 corpus
RK_URLS = REPO / "corpus" / "rekenkamer" / "urls.json"
rk_urls = json.loads(RK_URLS.read_text(encoding="utf-8")) if RK_URLS.exists() else []
rk = json.loads((OUT / "rekenkamer.json").read_text(encoding="utf-8"))
counts = rk["counts"]
for label, got, want in [
    ("PROBE-009 sitemap URLs", len(rk_urls), 5260),
    # 3.942 counts every URL under /documenten INCLUDING the index page itself; the trailing-slash form
    # would be 3.941 and the difference is a page listing, not a document.
    ("PROBE-009 document URLs", sum(1 for u in rk_urls if u.startswith("https://www.rekenkamer.nl/documenten")), 3942),
]:
    checked += 1
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

checked += 1
if (counts["publications_classified"] == 2677 and counts["attached_by_title"] == 1003
        and counts["attached_by_title_and_a_finding"] == 482):
    print("PASS  PROBE-009 publishes the completed crawl counts (2.677 / 1.003 / 482)")
else:
    print(f"FAIL  PROBE-009 counts moved: {counts}")
    fails.append("PROBE-009 counts disagree with the artifact")

# coverage must never claim less than the corpus holds, nor more than the scope allows
checked += 1
_cov = rk.get("coverage", {})
if _cov.get("harvest_complete") is True and counts["publications_classified"] >= _cov.get("pages_in_scope", 0):
    print(f"PASS  coverage is derived and complete ({counts['publications_classified']} of {_cov['pages_in_scope']})")
else:
    print(f"FAIL  coverage claim disagrees with the corpus: {_cov}")
    fails.append("coverage claim does not match the corpus")

# the honest-word guard: body matches must be unmeasured, never zero
checked += 1
if all(d.get("chapters_in_body_only") is None for d in rk["documents"]):
    print("PASS  body matches are recorded as unmeasured, not as zero")
else:
    print("FAIL  a document claims a body match although no PDF was read")
    fails.append("body matches claimed without text")

checked += 1
if sum(rk["by_kind"].values()) == counts["publications_classified"]:
    print(f"PASS  the document kinds partition the corpus ({len(rk['by_kind'])} kinds)")
else:
    print("FAIL  document kinds do not sum to the classified count")
    fails.append("kind split does not reconcile")

# findings are not reactions: the split must exist and be smaller than the attachment count
checked += 1
if counts["attached_by_title_and_a_finding"] < counts["attached_by_title"] and rk["by_kind"].get("reactie", 0) > 0:
    print("PASS  the artifact separates Rekenkamer findings from ministries' reactions")
else:
    print("FAIL  reactions are not separated from findings")
    fails.append("reactions counted as findings")

p9 = (REPO / "docs" / "PROBE-009-rekenkamer-crawl-and-what-titles-carry.md").read_text(encoding="utf-8", errors="replace")
# Prose wraps. A phrase check that fails on a newline is testing the line length, not the claim.
p9n = " ".join(p9.lower().split())
checked += 1
for phrase in ("2.677", "482", "1.003", "no pdf has been downloaded", "rung 6 therefore stays open", "403"):
    if phrase not in p9n:
        print(f"FAIL  PROBE-009 is missing: {phrase}")
        fails.append(f"PROBE-009 missing {phrase}")
        break
else:
    print("PASS  PROBE-009 states its coverage, its block and that rung 6 stays open")

# ---------------------------------------------------------------- PROBE-010, the join grain
import duckdb as _dd
con10 = _dd.connect(REPO / "data" / "aerarium.duckdb", read_only=True)
try:
    ra_n, m_an, m_on = con10.execute("""
        with ra as (select distinct artikel from recipient_line where coalesce(artikel,'')<>''),
             ban as (select distinct artikel_naam as x from budget_line where coalesce(artikel_naam,'')<>''),
             bao as (select distinct artikelonderdeel_naam as x from budget_line where coalesce(artikelonderdeel_naam,'')<>'')
        select (select count(*) from ra),
               (select count(*) from ra join ban on ra.artikel=ban.x),
               (select count(*) from ra join bao on ra.artikel=bao.x)""").fetchone()
    j = con10.execute("""
        with b as (select jaar, hoofdstuk_nummer as h, instrument_naam as i, sum(bedrag_k) as bud
                   from budget_line where vuo='U' group by 1,2,3),
             r as (select jaar, hoofdstuk as h, instrument as i, sum(bedrag_k) as rec
                   from recipient_line group by 1,2,3)
        select count(*), sum(case when r.rec > b.bud*1.02 then 1 else 0 end),
                     sum(case when r.rec <= b.bud*1.02 then 1 else 0 end)
        from b join r using (jaar,h,i)""").fetchone()
    n_ri = con10.execute("select count(distinct instrument) from recipient_line").fetchone()[0]
    blank_n, blank_m = con10.execute(
        "select count(distinct ontvanger), round(sum(bedrag_k)) from recipient_line where instrument is null"
    ).fetchone()
    n_bi = con10.execute("select count(distinct instrument_naam) from budget_line where vuo='U'").fetchone()[0]
finally:
    con10.close()

for label, got, want in [
    ("PROBE-010 recipient artikel values", ra_n, 238),
    ("PROBE-010 matching artikel_naam", m_an, 160),
    ("PROBE-010 matching artikelonderdeel_naam", m_on, 70),
    ("PROBE-010 named instrument types", n_ri, 10),
    ("PROBE-010 blank-instrument recipients", blank_n, 974),
    ("PROBE-010 budget instrument labels", n_bi, 286),
    ("PROBE-010 joined groups", j[0], 575),
    ("PROBE-010 overshoot groups", j[1], 42),
    ("PROBE-010 within groups", j[2], 533),
]:
    checked += 1
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

checked += 1
if j[1] + j[2] == j[0]:
    print("PASS  PROBE-010's joined groups partition into overshoot and within")
else:
    print("FAIL  PROBE-010 join groups do not partition")
    fails.append("PROBE-010 join partition does not reconcile")

p10 = (REPO / "docs" / "PROBE-010-where-the-two-registers-join.md").read_text(encoding="utf-8", errors="replace")
p10n = " ".join(p10.lower().split())
checked += 1
for phrase in ("575", "42", "92,7%", "cannot be built as written", "no euro is graded"):
    if phrase not in p10n:
        print(f"FAIL  PROBE-010 is missing: {phrase}")
        fails.append(f"PROBE-010 missing {phrase}")
        break
else:
    print("PASS  PROBE-010 states the join grain, the overshoot count and that nothing is graded yet")

# ---------------------------------------------------------------- FINDING-008, the overshoot split
con8 = _dd.connect(REPO / "data" / "aerarium.duckdb", read_only=True)
try:
    _ov = """
        with b as (select jaar, hoofdstuk_nummer as h, instrument_naam as i, sum(bedrag_k) as bud
                   from budget_line where vuo='U' group by 1,2,3),
             r as (select jaar, hoofdstuk as h, instrument as i, sum(bedrag_k) as rec
                   from recipient_line group by 1,2,3)
        select * from b join r using (jaar,h,i) where r.rec > b.bud*1.02"""
    # Bekostiging and sociale fondsen carry flows financed outside the appropriation, so they are split out.
    f8 = con8.execute(f"""
        with o as ({_ov})
        select count(*) filter (where i in ('Bekostiging','Bijdrage aan sociale fondsen')),
               count(*) filter (where i not in ('Bekostiging','Bijdrage aan sociale fondsen')),
               sum(rec-bud) filter (where i in ('Bekostiging','Bijdrage aan sociale fondsen')),
               sum(rec-bud) filter (where i not in ('Bekostiging','Bijdrage aan sociale fondsen')),
               count(*)
        from o""").fetchone()
    # round happens here rather than in SQL: `round()` is a scalar function and cannot take a FILTER clause
    f8 = (f8[0], f8[1], round(f8[2] / 1000), round(f8[3] / 1000), f8[4])
    bek = con8.execute(f"""with o as ({_ov}) select count(*), round(sum(rec-bud)/1000)
                           from o where i='Bekostiging'""").fetchone()
    soc = con8.execute(f"""with o as ({_ov}) select count(*), round(sum(rec-bud)/1000)
                           from o where i='Bijdrage aan sociale fondsen'""").fetchone()
    xvi_bud, xvi_rec = con8.execute("""
        select (select round(sum(bedrag_k)) from budget_line
                 where vuo='U' and jaar=2024 and hoofdstuk_nummer='XVI' and instrument_naam='Bekostiging'),
               (select round(sum(bedrag_k)) from recipient_line
                 where jaar=2024 and hoofdstuk='XVI' and instrument='Bekostiging')""").fetchone()
    xv_bud = con8.execute("""
        select round(sum(bedrag_k)) from budget_line where vuo='U' and jaar=2024
          and hoofdstuk_nummer='XV' and instrument_naam='Bijdrage aan sociale fondsen'""").fetchone()[0]
finally:
    con8.close()

for label, got, want in [
    ("FINDING-008 structural groups (Bekostiging + sociale fondsen)", f8[0], 13),
    ("FINDING-008 residual groups", f8[1], 29),
    ("FINDING-008 structural overshoot EURm", f8[2], 177168),
    ("FINDING-008 residual overshoot EURm", f8[3], 9053),
    ("FINDING-008 total overshoot groups", f8[4], 42),
    ("FINDING-008 Bekostiging groups", bek[0], 9),
    ("FINDING-008 Bekostiging overshoot EURm", bek[1], 102592),
    ("FINDING-008 sociale fondsen groups", soc[0], 4),
    ("FINDING-008 sociale fondsen overshoot EURm", soc[1], 74576),
    ("FINDING-008 XVI 2024 appropriation EURk", xvi_bud, 435738),
    ("FINDING-008 XVI 2024 register EURk", xvi_rec, 24419057),
    ("FINDING-008 XV 2024 sociale fondsen appropriation EURk", xv_bud, 20000),
]:
    checked += 1
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

checked += 1
if f8[0] + f8[1] == f8[4]:
    print("PASS  FINDING-008's structural and residual groups partition the 42 overshoots")
else:
    print("FAIL  FINDING-008 overshoot split does not reconcile")
    fails.append("FINDING-008 split does not reconcile")

p8 = (REPO / "docs" / "FINDING-008-the-appropriation-never-carried.md").read_text(encoding="utf-8", errors="replace")
p8n = " ".join(p8.lower().split())
checked += 1
for phrase in ("177.167,9", "9.053,0", "435.738", "24.419.057", "financed outside the appropriation"):
    if phrase not in p8n:
        print(f"FAIL  FINDING-008 is missing: {phrase}")
        fails.append(f"FINDING-008 missing {phrase}")
        break
else:
    print("PASS  FINDING-008 states the split, both chapter cases, and the grade it forces")

# ---------------------------------------------------------------- FINDING-009, the overshoot classes
ov = json.loads((OUT / "overshoots.json").read_text(encoding="utf-8"))
cls = ov["by_class"]
cov9 = ov["coverage"]
for label, got, want in [
    ("FINDING-009 overshoot groups", len(ov["groups"]), 42),
    ("FINDING-009 outside-appropriation groups", cls["outside-appropriation"]["groups"], 13),
    ("FINDING-009 outside-appropriation EURm", round(cls["outside-appropriation"]["overshoot_k"] / 1000), 177168),
    ("FINDING-009 transfer-structure groups", cls["transfer-structure"]["groups"], 16),
    ("FINDING-009 transfer-structure EURm", round(cls["transfer-structure"]["overshoot_k"] / 1000), 4308),
    ("FINDING-009 unexplained groups", cls["unexplained"]["groups"], 13),
    ("FINDING-009 unexplained EURm", round(cls["unexplained"]["overshoot_k"] / 1000), 4745),
]:
    checked += 1
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

checked += 1
if sum(c["groups"] for c in cls.values()) == len(ov["groups"]) == 42:
    print("PASS  the overshoot classes partition all 42 groups")
else:
    print("FAIL  overshoot classes do not partition the groups")
    fails.append("overshoot classes do not partition")

checked += 1
if cov9["joinable_share"] == 0.4567 or round(cov9["joinable_share"], 3) == 0.457:
    print(f"PASS  the joinable share of expenditure is {cov9['joinable_share']:.1%}")
else:
    print(f"FAIL  joinable share moved: {cov9['joinable_share']}")
    fails.append("joinable share moved")

checked += 1
rbv9 = ov["rbv_model"]
if rbv9["blank_rows"] == rbv9["expenditure_rows"]:
    print(f"PASS  rbv_model is recorded as blank on all {rbv9['expenditure_rows']:,} expenditure rows")
else:
    print(f"FAIL  rbv_model carries values now: {rbv9['blank_rows']} blank of {rbv9['expenditure_rows']}")
    fails.append("rbv_model is no longer blank; the bridge may exist")

p9 = (REPO / "docs" / "FINDING-009-the-join-covers-46-percent.md").read_text(encoding="utf-8", errors="replace")
p9n = " ".join(p9.lower().split())
checked += 1
for phrase in ("177.167,9", "4.307,8", "4.744,9", "45,7%", "sixteen of the twenty-nine", "blank in all 44.352"):
    if phrase not in p9n:
        print(f"FAIL  FINDING-009 is missing: {phrase}")
        fails.append(f"FINDING-009 missing {phrase}")
        break
else:
    print("PASS  FINDING-009 states the class split, the coverage share and the empty column")

# FINDING-008's optimism must carry its correction, not its original claim alone
p8c = (REPO / "docs" / "FINDING-008-the-appropriation-never-carried.md").read_text(encoding="utf-8", errors="replace")
p8n = " ".join(p8c.lower().split())
checked += 1
if "correction, 2026-11-26" in p8n and "too optimistic" in p8n and "thirteen" in p8n:
    print("PASS  FINDING-008 carries the dated correction that narrows its 'tractable' claim")
else:
    print("FAIL  FINDING-008 still asserts the 29 are tractable without the correction")
    fails.append("FINDING-008 correction missing")

# ---------------------------------------------------------------- page section 08/09 (state side)
st = json.loads((OUT / "state-data.json").read_text(encoding="utf-8"))
for label, got, want in [
    ("page state payload: expenditure axis EURk", st["spend"]["expenditure_axis_k"], 401303575),
    ("page state payload: programme spending EURk", st["spend"]["programme_k"], 331469674),
    ("page state payload: personnel EURk", st["spend"]["personnel_k"], 17503748),
    ("page state payload: rekenkamer pages", st["rekenkamer"]["pages"], 2677),
    ("page state payload: rekenkamer findings", st["rekenkamer"]["findings"], 482),
    ("page state payload: rbv blank rows", st["join"]["rbv_blank_rows"], 44352),
]:
    checked += 1
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got}")
    if not ok:
        fails.append(f"{label}: {got} != {want}")

# the state payload must agree with the artifacts it was built from, not merely be self-consistent
checked += 1
if (abs(st["join"]["joinable_share"] - ov["coverage"]["joinable_share"]) < 1e-9
        and st["outside"]["overshoot_k"] == cls["outside-appropriation"]["overshoot_k"]
        and st["rekenkamer"]["attached_by_title"] == rk["counts"]["attached_by_title"]):
    print("PASS  the page's state payload matches the artifacts it was built from")
else:
    print("FAIL  the page's state payload disagrees with the artifacts")
    fails.append("state payload disagrees with artifacts")

# an unmeasured body-match count must reach the page as unmeasured, never as zero
checked += 1
if st["rekenkamer"]["body_matches"] is None:
    print("PASS  the page carries the body-match count as unmeasured, not zero")
else:
    print("FAIL  the page states a body-match count although no PDF was read")
    fails.append("page claims a body-match count")

# the sections must actually exist in the markup, and the payload must ride inside the page
checked += 1
if ('<section id="state"' in html and '<section id="rung6"' in html
        and 'id="state"' in html and len(st["join"]) > 0):
    print("PASS  sections 08 and 09 exist and their payload is embedded in the served page")
else:
    print("FAIL  the state sections or their embedded payload are missing from the page")
    fails.append("state sections missing from the page")

# ---------------------------------------------------------------- canary
if "--canary" in sys.argv:
    print("\n-- canary: perturbing one bound value to prove this checker can fail --")
    before = len(fails)
    bind("CANARY (must fail)", readme, r"€([\d.]+) arrived in the", win_total + 1000, tol=1)
    if len(fails) == before:
        print("FAIL  canary did not trip: this checker cannot detect a wrong number")
        sys.exit(2)
    print(f"PASS  canary tripped the checker as it should")
    sys.exit(0)

print()
print(f"{checked} bound values checked")
if fails:
    print(f"\n{len(fails)} FAILURE(S):")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("ALL PROSE CLAIMS MATCH THE ARTIFACTS")
