"""
Static geographic data for Phase 2: zone center coordinates (geocoded via
OSMnx/Nominatim, real place lookups) and Chennai Metrowater's real filling
points, which the tankers refill at.
"""

from __future__ import annotations
import csv
import os

# Zone name -> (lat, lon), geocoded via ox.geocode() against OpenStreetMap.
# All 15 Chennai Metrowater / GCC zones (see data/metrowater/zones.csv).
ZONE_COORDS: dict[str, tuple[float, float]] = {
    # The 8 entitled in Phase 0's sample snapshot -- the original set.
    "thiruvotriyur": (13.1718028, 80.3052689),
    "manali": (13.1810602, 80.2694192),
    "royapuram": (13.1042898, 80.2936125),
    "teynampet": (13.0443237, 80.2498455),
    "kodambakkam": (13.049207, 80.2242829),
    "alandur": (13.0028216, 80.1719186),
    "perungudi": (12.9710239, 80.2418051),
    "tondiarpet": (13.1275202, 80.2819242),
    # The other 7, so a volunteer report from any zone can be routed.
    # Each is the representative point of OSM's official "Zone N <name>"
    # boundary relation, whose numbering matches the Metrowater zone map.
    "madhavaram": (13.1421473, 80.2323786),       # Zone 3
    "thiruvika_nagar": (13.1208988, 80.2295103),  # Zone 6
    "ambattur": (13.1055654, 80.1639586),         # Zone 7
    "anna_nagar": (13.088249, 80.2073398),        # Zone 8
    "valasaravakkam": (13.0415799, 80.1724952),   # Zone 11
    "adyar": (13.00645, 80.2577791),              # Zone 13
    # Plain "Sholinganallur" geocodes to the whole taluk (reaching west to
    # 80.17); this is the "Zone 15 Sholinganallur" relation instead.
    "sozhanganallur": (12.8935, 80.2321),         # Zone 15
}

# Chennai Metrowater's real filling points, from its published list of
# filling-point addresses (data/metrowater/filling_points.csv). Each address
# was geocoded against OpenStreetMap; the CSV records how precisely
# ("street", "locality" or "approximate") and what it matched. A point
# with no location yet (Southern Head Works) is skipped, not guessed.
FILLING_POINTS_CSV = os.path.join(
    os.path.dirname(__file__), "..", "data", "metrowater", "filling_points.csv"
)


def _load_filling_points() -> list[dict]:
    with open(FILLING_POINTS_CSV, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["lat"] and r["lon"]]


_FILLING_POINTS = _load_filling_points()
SOURCE_STATIONS: dict[str, tuple[float, float]] = {
    r["key"]: (float(r["lat"]), float(r["lon"])) for r in _FILLING_POINTS
}
# Display names, e.g. "fp_kk_nagar" -> "K.K.Nagar Filling Point".
FILLING_POINT_NAMES: dict[str, str] = {r["key"]: r["name"] for r in _FILLING_POINTS}

# Bounding box covering all zones + stations with a small margin, used to
# fetch a bounded (not city-wide) road network -- keeps Phase 2 fast and
# fits Rule 5 (start small).
ALL_POINTS = list(ZONE_COORDS.values()) + list(SOURCE_STATIONS.values())
_lats = [p[0] for p in ALL_POINTS]
_lons = [p[1] for p in ALL_POINTS]
MARGIN_DEG = 0.02
BBOX = (
    max(_lats) + MARGIN_DEG,  # north
    min(_lats) - MARGIN_DEG,  # south
    max(_lons) + MARGIN_DEG,  # east
    min(_lons) - MARGIN_DEG,  # west
)
