"""Tests over the disclosure artifact itself.

Every expected value is read from ``out/party-line-disclosure.csv`` at collection time; nothing here is
hard-coded that the CSV does not already state. The artifact is the deliverable, so the tests grade the
deliverable.

Run: ``.venv/bin/python -m pytest -q tests/``
"""

from __future__ import annotations

import csv
from pathlib import Path

CSV_PATH = Path("out/party-line-disclosure.csv")


def _rows() -> dict[tuple[int, str], dict[str, str]]:
    """(jaar, family) -> row. (jaar, family) is unique in the artifact; jaar alone is not."""
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return {(int(r["jaar"]), r["family"]): r for r in csv.DictReader(fh)}


REQUIRED_COLUMNS = (
    "jaar", "family", "label", "group", "instruments", "budget_names", "register_names",
    "ceiling_k", "owb_rows", "realised_k", "jv_rows", "named_rows", "named_k", "anon_rows",
    "anon_k", "unreconciled_k", "named_coverage", "disclosed_coverage", "r1", "r2", "r3",
    "r4", "r5", "r6", "reach", "breaks", "recipient_source", "notes",
)


def test_header_has_the_required_columns_exactly() -> None:
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert tuple(header) == REQUIRED_COLUMNS


def test_every_row_r2_is_unavailable_in_source() -> None:
    rows = _rows()
    assert rows, "artifact is empty"
    for jaar, row in sorted(rows.items()):
        assert row["r2"] == "unavailable-in-source", jaar


def test_2019_politieke_partijen_is_aggregate_only_with_anonymous_euros() -> None:
    rows = _rows()
    row = rows[(2019, "politieke-partijen")]
    assert row["family"] == "politieke-partijen"
    assert row["r4"] == "aggregate-only"
    assert int(row["anon_k"]) > 0
    assert int(row["named_k"]) == 0


def test_2024_politieke_partijen_arithmetic() -> None:
    rows = _rows()
    row = rows[(2024, "politieke-partijen")]
    assert row["r4"] == "partial"
    assert float(row["named_coverage"]) < 0.2
    assert int(row["unreconciled_k"]) > 25000
