"""Scheme families: the curated normalisation table that stands in for a missing key.

Scheme names in the sources drift, truncate and carry typos across years, and the two sources do not even
agree on the name of the same line:

    budget tables   Politieke partijen                    (2016-2026)
    register        Subsidiering wet Financiering Politieke Partijen   (2017-2018)
    register        Politieke partijen                    (2019-2024)

    budget tables   Toer. onderst. Pol A                  (2020)
                    Toerusting en ondersteuning politieke ambtsdragers  (2021-2023)
                    Toerusting en ondersteuning politieke am            (2024, truncated)

    budget tables   Nederlands Fonds voor Regionale Partnerschappen MATRA  (2021-2026)
    register        NFRP Politieke Partijen              (2018-2024)

So the scheme name is not a key. A *family* is the stable identity; the names are evidence of drift and are
carried in the artifact's `budget_names` and `register_names` columns rather than folded away. Anything that
matches no family is reported as UNMAPPED and never dropped: an unmapped name is a gap in this table, not an
absence of spending.
"""

from __future__ import annotations

import re

UNMAPPED = "unmapped"


class Family:
    __slots__ = ("family", "label", "group", "note", "register_only")

    def __init__(self, family: str, label: str, group: str, *, note: str = "", register_only: bool = False):
        self.family = family
        self.label = label
        self.group = group
        self.note = note
        self.register_only = register_only

    def years(self, conn) -> list[int]:
        """Every year in which either source says something about this family."""
        rows = conn.execute(
            """
            SELECT DISTINCT jaar FROM (
                SELECT jaar, regeling_naam AS nama FROM budget_line
                UNION ALL
                SELECT jaar, regeling AS nama FROM recipient_line
            ) t JOIN scheme_map m ON t.nama = m.nama
            WHERE m.family = ? ORDER BY 1
            """,
            [self.family],
        ).fetchall()
        return [int(y) for (y,) in rows]


class Scheme:
    __slots__ = ("family", "pattern", "variants", "note")

    def __init__(self, family: str, pattern: str, variants: tuple[str, ...], note: str = ""):
        self.family = family
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.variants = variants
        self.note = note

    def matches(self, name: str | None) -> bool:
        return bool(name) and bool(self.pattern.match(name.strip()))


FAMILIES: tuple[str, ...] = (
    "politieke-partijen",
    "decentrale-politieke-partijen",
    "toerusting-politieke-ambtsdragers",
    "nfrp-politieke-partijen",
)

_FAMILY_SPECS: dict[str, Family] = {
    "politieke-partijen": Family(
        family="politieke-partijen",
        label="Politieke partijen (Wfpp-subsidie)",
        group="BZK art. 1.2 Democratie",
        note="The Wfpp party subsidy. Chapter VII, artikel 1, artikelonderdeel 2 Democratie.",
    ),
    "decentrale-politieke-partijen": Family(
        family="decentrale-politieke-partijen",
        label="Decentrale politieke partijen",
        group="BZK art. 1.2 Democratie",
        note="Ceiling for local and regional parties. First appears in 2024. 2025: 8.382k ceiling, 0 realised.",
    ),
    "toerusting-politieke-ambtsdragers": Family(
        family="toerusting-politieke-ambtsdragers",
        label="Toerusting en ondersteuning politieke ambtsdragers",
        group="BZK art. 1.2 Democratie",
        note="Equipment and support for officeholders: raadsleden, griffiers, wethouders, Kennispunt, Sioo.",
    ),
    "nfrp-politieke-partijen": Family(
        family="nfrp-politieke-partijen",
        label="NFRP Politieke Partijen (internationale stichtingen van partijen)",
        group="BZ art. Veiligheid en stabiliteit",
        note=(
            "The begroting names the parent programme 'Nederlands Fonds voor Regionale Partnerschappen "
            "MATRA' and does not split out the party sub-scheme, so there is no ceiling to grade at r1. "
            "The register does split it out, and names the recipients with KvK: Eduardo Frei (CDA), Max "
            "van der Stoel (PvdA), IDI (D66), FICDD (CU), SGP-Internationaal, Haya van Someren (VVD), "
            "Animal Politics (PvdD), GroenLinks International, Forum for Democracy International, Volt "
            "There, SP Internationaal."
        ),
        register_only=True,
    ),
}


def family_spec(family: str) -> Family:
    return _FAMILY_SPECS[family]


# Tested in order. Anchored where the names would otherwise collide
# ('Politieke partijen' must not swallow 'Decentrale politieke partijen').
SCHEMES: tuple[Scheme, ...] = (
    Scheme(
        family="politieke-partijen",
        pattern=r"^politieke partijen$",
        variants=("Politieke partijen", "Politieke Partijen", "POLITIEKE PARTIJEN"),
    ),
    Scheme(
        family="politieke-partijen",
        pattern=r"^subsidiering wet financiering politieke partijen$",
        variants=("Subsidiering wet Financiering Politieke Partijen",),
        note=(
            "The register's 2017-2018 name for the same line. Same money: register 17.994k vs JV 17.992k "
            "(2017), 16.124k vs 16.125k (2018)."
        ),
    ),
    Scheme(
        family="decentrale-politieke-partijen",
        pattern=r"^decentrale politieke partijen$",
        variants=("Decentrale politieke partijen",),
    ),
    Scheme(
        family="toerusting-politieke-ambtsdragers",
        pattern=r"^toer\.? *(usting|onderst)",
        variants=(
            "Toer. onderst. Pol A",
            "Toerusting en ondersteuning politieke ambtsdragers",
            "Toerusting en ondersteuning politieke am",
        ),
    ),
    Scheme(
        family="nfrp-politieke-partijen",
        pattern=r"^nfrp politieke partijen",
        variants=(
            "NFRP Politieke Partijen Programma 2018",
            "NFRP Politieke Partijen Programma 2022",
            "NFRP Politieke Partijen 2023",
            "NFRP Politieke Partijen",
        ),
    ),
)


def classify(name: str | None) -> str:
    """Return the canonical family for a scheme name, or UNMAPPED."""
    for scheme in SCHEMES:
        if scheme.matches(name):
            return scheme.family
    return UNMAPPED


def observed_variants() -> dict[str, tuple[str, ...]]:
    out: dict[str, list[str]] = {}
    for scheme in SCHEMES:
        out.setdefault(scheme.family, []).extend(scheme.variants)
    return {k: tuple(v) for k, v in out.items()}
