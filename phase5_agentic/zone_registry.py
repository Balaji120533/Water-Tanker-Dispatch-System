"""
Which Metrowater zone does a place belong to?

Reads the reference data in data/metrowater/ (built by
scripts/build_metrowater_data.py from the Metrowater zone map and
OpenStreetMap boundaries) and answers that question deterministically.

RULE 2: this lookup is deliberately NOT done by the language model. A
volunteer's "Vadapalani" becoming Zone 10 Kodambakkam decides where a
tanker goes, so it must come from a table a reviewer can open and check --
not from what a model happens to remember about Chennai. The LLM only
copies out the place name the volunteer typed; this module places it.

Pure module: no HTTP, no LLM calls.
"""

from __future__ import annotations
import csv
import difflib
import os
import re
from dataclasses import dataclass, field

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "metrowater")


@dataclass(frozen=True)
class MetroZone:
    zone_no: int
    roman: str
    key: str         # identifier used by the logic engine / CSP / routing
    name: str        # as printed on the Metrowater map
    divisions: tuple[int, ...]

    def label(self) -> str:
        return f"Zone {self.zone_no} {self.name}"


@dataclass
class Resolution:
    """
    kind:
      "zone"      -- the place IS a zone ("Anna Nagar", "zone 10", "ward 130")
      "locality"  -- a locality inside exactly one zone ("Vadapalani")
      "ambiguous" -- a locality name used in several zones ("Gandhi Nagar")
      "unknown"   -- not inside any of the 15 zones
    """
    kind: str
    zone: MetroZone | None = None
    locality: str | None = None
    ward: int | None = None
    candidates: list[MetroZone] = field(default_factory=list)


def _normalise(text: str) -> str:
    """
    Fold the spelling differences people actually type: case, dots, dashes,
    and spaced initials ("K. K. Nagar", "KK Nagar" and "k k nagar" all
    become "kk nagar").
    """
    t = re.sub(r"[.\-,'/()]", " ", text.lower())
    t = re.sub(r"\s+", " ", t).strip()
    # Merge runs of single letters: "t v k nagar" -> "tvk nagar".
    t = re.sub(r"\b(?:[a-z] )+[a-z]\b", lambda m: m.group(0).replace(" ", ""), t)
    return t


def _expand(ranges: str) -> tuple[int, ...]:
    out = []
    for part in ranges.split(";"):
        lo, hi = (int(x) for x in part.split("-"))
        out.extend(range(lo, hi + 1))
    return tuple(out)


def _load_zones() -> list[MetroZone]:
    with open(os.path.join(DATA_DIR, "zones.csv"), encoding="utf-8") as f:
        return [
            MetroZone(int(r["zone_no"]), r["roman"], r["key"], r["name"], _expand(r["division_numbers"]))
            for r in csv.DictReader(f)
        ]


ZONES: list[MetroZone] = _load_zones()
ZONE_BY_KEY = {z.key: z for z in ZONES}
ZONE_BY_NO = {z.zone_no: z for z in ZONES}
ZONE_BY_ROMAN = {z.roman.lower(): z for z in ZONES}
DIVISION_TO_ZONE = {d: z for z in ZONES for d in z.divisions}

# Every name that should mean the zone itself. The printed name and the
# code key come from zones.csv; the rest are spelling variants of those same
# names (OSM, for example, spells Zone 1 "Tiruvottiyur" and Zone 15
# "Sholinganallur") -- no geographic claims are added here.
_ZONE_NAMES: dict[str, MetroZone] = {}
for _z in ZONES:
    _ZONE_NAMES[_normalise(_z.name)] = _z
    _ZONE_NAMES[_normalise(_z.key.replace("_", " "))] = _z
for _variant, _key in {
    "tiruvottiyur": "thiruvotriyur", "thiruvottiyur": "thiruvotriyur",
    "tiruvotriyur": "thiruvotriyur",
    "thiru vi ka nagar": "thiruvika_nagar", "tvk nagar": "thiruvika_nagar",
    "thiruvi ka nagar": "thiruvika_nagar",
    "sholinganallur": "sozhanganallur", "shozhinganallur": "sozhanganallur",
    "sozhinganallur": "sozhanganallur", "cholinganallur": "sozhanganallur",
    "annanagar": "anna_nagar",
}.items():
    _ZONE_NAMES[_variant] = ZONE_BY_KEY[_key]


def _load_localities() -> dict[str, list[tuple[MetroZone, str, int | None]]]:
    """normalised name -> [(zone, name as in OSM, ward), ...]"""
    table: dict[str, list] = {}
    with open(os.path.join(DATA_DIR, "localities.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ward = int(r["ward"]) if r["ward"] else None
            table.setdefault(_normalise(r["name"]), []).append(
                (ZONE_BY_NO[int(r["zone_no"])], r["name"], ward)
            )
    return table


LOCALITIES = _load_localities()

# Common short forms OSM does not carry. Each points at an OSM locality
# name, so the ZONE still comes from the boundary data, not from here.
LOCALITY_ALIASES = {
    "t nagar": "thiyagaraya nagar",
    "thyagaraya nagar": "thiyagaraya nagar",
    "thyagaraja nagar": "thiyagaraya nagar",
}

_WARD_RE = re.compile(r"\b(?:ward|division|div)\s*(?:no\.?|number|#)?\s*(\d{1,3})\b", re.I)
_ZONE_NO_RE = re.compile(r"\bzone\s*(?:no\.?|number|#)?\s*(\d{1,2}|[ivx]{1,4})\b", re.I)


def zone_from_numbers(message: str) -> Resolution | None:
    """
    "ward 130", "division 64", "zone 10", "zone X" -> the zone, using the
    Metrowater map's own numbering. Returns None if no valid number is given.
    """
    m = _WARD_RE.search(message)
    if m and int(m.group(1)) in DIVISION_TO_ZONE:
        ward = int(m.group(1))
        return Resolution("zone", zone=DIVISION_TO_ZONE[ward], ward=ward)

    m = _ZONE_NO_RE.search(message)
    if m:
        token = m.group(1).lower()
        zone = ZONE_BY_NO.get(int(token)) if token.isdigit() else ZONE_BY_ROMAN.get(token)
        if zone:
            return Resolution("zone", zone=zone)
    return None


def _from_locality_rows(rows) -> Resolution:
    zones = {z.zone_no: z for z, _name, _ward in rows}
    if len(zones) == 1:
        zone, name, ward = rows[0]
        return Resolution("locality", zone=zone, locality=name, ward=ward)
    return Resolution(
        "ambiguous", locality=rows[0][1],
        candidates=sorted(zones.values(), key=lambda z: z.zone_no),
    )


def resolve_place(place: str) -> Resolution:
    """Place a name the volunteer typed into one of the 15 zones, if possible."""
    if not place or not place.strip():
        return Resolution("unknown")

    numbered = zone_from_numbers(place)
    if numbered:
        return numbered

    key = _normalise(place)
    key = re.sub(r"\b(area|zone|side|region)$", "", key).strip()
    key = LOCALITY_ALIASES.get(key, key)

    # A zone's own name wins over a same-named colony elsewhere: "Anna
    # Nagar" is Zone 8, even though Zone 1 also has a small Anna Nagar.
    if key in _ZONE_NAMES:
        return Resolution("zone", zone=_ZONE_NAMES[key])
    if key in LOCALITIES:
        return _from_locality_rows(LOCALITIES[key])

    # Tolerate small spelling slips ("vadapalni", "velacheri"), but only
    # when exactly one known name is clearly closest -- never a coin-flip.
    names = list(_ZONE_NAMES) + list(LOCALITIES)
    close = difflib.get_close_matches(key, names, n=2, cutoff=0.85)
    if close and (len(close) == 1 or
                  difflib.SequenceMatcher(None, key, close[0]).ratio()
                  - difflib.SequenceMatcher(None, key, close[1]).ratio() > 0.05):
        best = close[0]
        if best in _ZONE_NAMES:
            return Resolution("zone", zone=_ZONE_NAMES[best])
        return _from_locality_rows(LOCALITIES[best])

    return Resolution("unknown")


def zone_list_text() -> str:
    """All 15 zones, numbered as on the Metrowater map, one per line."""
    return "\n".join(f"{z.zone_no}. {z.name}" for z in ZONES)
