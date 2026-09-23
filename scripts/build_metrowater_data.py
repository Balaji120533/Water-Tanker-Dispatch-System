"""
Builds the zone / locality reference data in data/metrowater/ from two
sources, and refuses to write anything if they disagree:

  1. The Chennai Metrowater zone & division map (project owner's PDF,
     "Metrowater zone and division.pdf"). Its table gives each of the 15
     zones' number, name and division (ward) numbers -- transcribed below
     as METROWATER_ZONES. This is the authority for which zone is which.

  2. OpenStreetMap, which carries the same Greater Chennai Corporation
     boundaries as relations named "Zone N <name>" and "Ward N", plus
     ~500 named localities (suburbs, neighbourhoods). A locality's zone is
     decided by which official zone polygon it falls inside -- a spatial
     fact, not anyone's recollection.

Cross-check: every OSM ward polygon must sit inside the zone that the PDF's
division table assigns to that ward number. If even one disagrees, the
numbering schemes don't match and nothing is written.

Run from the repo root:  python scripts/build_metrowater_data.py
"""

from __future__ import annotations
import csv
import os
import re
import sys

import geopandas as gpd
import osmnx as ox

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR = os.path.join(ROOT, "data", "metrowater")

# --- Transcribed from the Metrowater PDF's zone table -----------------------
# (zone_no, roman, key used across this codebase, name as printed, divisions)
# Keys are the identifiers Phase 0's knowledge base already uses; the
# printed name is what volunteers see.
METROWATER_ZONES = [
    (1, "I", "thiruvotriyur", "Thiruvottiyur", [(1, 14)]),
    (2, "II", "manali", "Manali", [(15, 21)]),
    (3, "III", "madhavaram", "Madhavaram", [(22, 33)]),
    (4, "IV", "tondiarpet", "Tondiarpet", [(34, 48)]),
    (5, "V", "royapuram", "Royapuram", [(49, 63)]),
    (6, "VI", "thiruvika_nagar", "Thiru-Vi-Ka Nagar", [(64, 78)]),
    (7, "VII", "ambattur", "Ambattur", [(79, 93)]),
    (8, "VIII", "anna_nagar", "Anna Nagar", [(94, 108)]),
    (9, "IX", "teynampet", "Teynampet", [(109, 126)]),
    (10, "X", "kodambakkam", "Kodambakkam", [(127, 142)]),
    (11, "XI", "valasaravakkam", "Valasaravakkam", [(143, 155)]),
    (12, "XII", "alandur", "Alandur", [(156, 167)]),
    (13, "XIII", "adyar", "Adyar", [(170, 182)]),
    # Zone XIV is the one non-contiguous range on the map: 168, 169, 183-191.
    (14, "XIV", "perungudi", "Perungudi", [(168, 169), (183, 191)]),
    (15, "XV", "sozhanganallur", "Shozhinganallur", [(192, 200)]),
]
# Division counts exactly as printed in the PDF, checked against the ranges.
PRINTED_DIVISION_COUNTS = {1: 14, 2: 7, 3: 12, 4: 15, 5: 15, 6: 15, 7: 15, 8: 15,
                           9: 18, 10: 16, 11: 13, 12: 12, 13: 13, 14: 11, 15: 9}

PLACE_TYPES = ["suburb", "neighbourhood", "locality", "quarter", "village", "hamlet", "town"]


def division_to_zone() -> dict[int, int]:
    table = {}
    for zone_no, _roman, _key, _name, ranges in METROWATER_ZONES:
        for lo, hi in ranges:
            for d in range(lo, hi + 1):
                assert d not in table, f"division {d} listed twice"
                table[d] = zone_no
    return table


def check_pdf_transcription(table: dict[int, int]) -> None:
    assert sorted(table) == list(range(1, 201)), "divisions must cover 1..200 exactly once"
    for zone_no, *_ in METROWATER_ZONES:
        n = sum(1 for z in table.values() if z == zone_no)
        assert n == PRINTED_DIVISION_COUNTS[zone_no], (
            f"zone {zone_no}: ranges give {n} divisions, PDF prints {PRINTED_DIVISION_COUNTS[zone_no]}"
        )


def fetch_boundaries():
    g = ox.features_from_place("Chennai, Tamil Nadu, India", tags={"boundary": "administrative"})
    g = g[g.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].reset_index(drop=True)
    names = g["name"].fillna("")

    zones = g[names.str.match(r"^Zone \d+ ")].copy()
    zones["zone_no"] = zones["name"].str.extract(r"^Zone (\d+) ")[0].astype(int)

    wards = g[names.str.match(r"^Ward \d+$")].copy()
    wards["ward"] = wards["name"].str.extract(r"^Ward (\d+)$")[0].astype(int)
    return zones[["zone_no", "name", "geometry"]], wards[["ward", "geometry"]]


def cross_check_wards(zones, wards, table) -> int:
    pts = gpd.GeoDataFrame(wards[["ward"]], geometry=wards.geometry.representative_point(), crs=4326)
    joined = gpd.sjoin(pts, zones[["zone_no", "geometry"]], predicate="within", how="left")
    joined["pdf_zone"] = joined["ward"].map(table)
    bad = joined[joined["zone_no"] != joined["pdf_zone"]]
    if len(bad):
        print(bad[["ward", "zone_no", "pdf_zone"]].to_string())
        sys.exit("OSM ward boundaries disagree with the PDF division table -- not writing data.")
    return len(joined)


def fetch_localities(zones, wards):
    p = ox.features_from_place("Chennai, Tamil Nadu, India", tags={"place": PLACE_TYPES})
    p = p[p["name"].notna()].reset_index(drop=True)
    p = gpd.GeoDataFrame(p[["name", "place"]], geometry=p.geometry.representative_point(), crs=4326)

    p = gpd.sjoin(p, zones[["zone_no", "geometry"]], predicate="within", how="inner")
    p = p.drop(columns="index_right")
    p = gpd.sjoin(p, wards[["ward", "geometry"]], predicate="within", how="left")

    rows = {}
    for r in p.itertuples():
        name = re.sub(r"\s+", " ", str(r.name)).strip()
        key = (name.lower(), int(r.zone_no))
        if key in rows:
            continue  # same name mapped twice inside one zone -- keep the first
        rows[key] = {
            "name": name,
            "zone_no": int(r.zone_no),
            "ward": "" if r.ward != r.ward else int(r.ward),  # NaN -> blank
            "place_type": r.place,
            "lat": round(r.geometry.y, 6),
            "lon": round(r.geometry.x, 6),
        }
    return sorted(rows.values(), key=lambda r: (r["zone_no"], r["name"].lower()))


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main():
    table = division_to_zone()
    check_pdf_transcription(table)

    zones, wards = fetch_boundaries()
    found = sorted(zones["zone_no"])
    assert found == list(range(1, 16)), f"expected OSM zones 1..15, got {found}"
    for zone_no, _roman, _key, printed, _ranges in METROWATER_ZONES:
        osm_name = zones.loc[zones["zone_no"] == zone_no, "name"].iloc[0]
        print(f"  zone {zone_no:>2}  PDF: {printed:<18} OSM: {osm_name}")

    checked = cross_check_wards(zones, wards, table)
    print(f"wards cross-checked against the PDF table: {checked}/{checked} agree")

    localities = fetch_localities(zones, wards)
    print(f"localities mapped to a zone: {len(localities)}")

    os.makedirs(OUT_DIR, exist_ok=True)
    write_csv(
        os.path.join(OUT_DIR, "zones.csv"),
        ["zone_no", "roman", "key", "name", "divisions", "division_numbers"],
        [
            {
                "zone_no": zone_no, "roman": roman, "key": key, "name": name,
                "divisions": PRINTED_DIVISION_COUNTS[zone_no],
                "division_numbers": ";".join(f"{lo}-{hi}" for lo, hi in ranges),
            }
            for zone_no, roman, key, name, ranges in METROWATER_ZONES
        ],
    )
    write_csv(
        os.path.join(OUT_DIR, "localities.csv"),
        ["name", "zone_no", "ward", "place_type", "lat", "lon"],
        localities,
    )
    print(f"wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
