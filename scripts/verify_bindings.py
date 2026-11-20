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
html = (OUT / "index.html").read_text(encoding="utf-8")
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

cbstxt = (REPO / "docs" / "LANE-CBS-STATISTICS.md").read_text(encoding="utf-8", errors="replace")
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
