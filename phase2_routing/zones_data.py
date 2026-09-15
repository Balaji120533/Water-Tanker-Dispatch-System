"""
Static geographic data for Phase 2: zone center coordinates (geocoded via
OSMnx/Nominatim, real place lookups) and synthetic source-station points
(confirmed with the project owner — NOT real Metrowater depot locations).
"""

from __future__ import annotations

# Zone name -> (lat, lon), geocoded via ox.geocode() against OpenStreetMap.
# These are the 8 entitled zones from Phase 0's forward-chaining output.
ZONE_COORDS: dict[str, tuple[float, float]] = {
    "thiruvotriyur": (13.1718028, 80.3052689),
    "manali": (13.1810602, 80.2694192),
    "royapuram": (13.1042898, 80.2936125),
    "teynampet": (13.0443237, 80.2498455),
    "kodambakkam": (13.049207, 80.2242829),
    "alandur": (13.0028216, 80.1719186),
    "perungudi": (12.9710239, 80.2418051),
    "tondiarpet": (13.1275202, 80.2819242),
}

# SYNTHETIC source (filling) stations — confirmed with project owner, not
# real published Metrowater depot coordinates. Spread across the north and
# south clusters of our zone set for reasonable coverage.
SOURCE_STATIONS: dict[str, tuple[float, float]] = {
    "station_a": (13.15, 80.29),   # north cluster
    "station_b": (13.10, 80.28),   # royapuram / tondiarpet area
    "station_c": (13.05, 80.24),   # teynampet / kodambakkam area
    "station_d": (13.00, 80.20),   # alandur area
    "station_e": (12.97, 80.24),   # perungudi area
}

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
