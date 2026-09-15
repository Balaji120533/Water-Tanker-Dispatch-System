"""
Computes travel time/distance between every source station and every zone,
using our custom A* over the real road graph. Assumes a flat average speed
to convert distance -> time (no live traffic data available for this
academic simulation).
"""

from __future__ import annotations
import json
import os
from graph_loader import load_graph, nearest_node
from zones_data import ZONE_COORDS, SOURCE_STATIONS
from astar import astar_path

AVG_SPEED_KMPH = 25.0  # plausible average city-driving speed for a loaded tanker

CACHE_PATH = os.path.join(os.path.dirname(__file__), "cache", "travel_times.json")


def _load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        distances = {tuple(k.split("|")): v for k, v in raw["distances"].items()}
        times_minutes = {tuple(k.split("|")): v for k, v in raw["times_minutes"].items()}
        return distances, times_minutes
    return None


def _save_cache(distances, times_minutes):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    raw = {
        "distances": {f"{a}|{b}": v for (a, b), v in distances.items()},
        "times_minutes": {f"{a}|{b}": v for (a, b), v in times_minutes.items()},
    }
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(raw, f)


def build_travel_time_matrix(graph=None, force_refresh: bool = False):
    """
    Returns:
      distances: dict[(point_name_a, point_name_b)] -> meters
      times_minutes: dict[(point_name_a, point_name_b)] -> minutes
    Computed both directions (station->zone and zone->station), since a
    tanker travels station -> zone -> (eventually) back to a station.
    Cached to disk (JSON) since this is 80 A* solves over a large real
    graph -- static data, no reason to recompute on every run.
    """
    if not force_refresh:
        cached = _load_cache()
        if cached is not None:
            return cached

    graph = graph if graph is not None else load_graph()

    all_points = {**SOURCE_STATIONS, **ZONE_COORDS}
    node_of = {name: nearest_node(graph, lat, lon) for name, (lat, lon) in all_points.items()}

    distances = {}
    times_minutes = {}

    station_names = list(SOURCE_STATIONS.keys())
    zone_names = list(ZONE_COORDS.keys())

    pairs = [(s, z) for s in station_names for z in zone_names]
    pairs += [(z, s) for s in station_names for z in zone_names]  # return trips
    pairs += [(a, b) for a in zone_names for b in zone_names if a != b]  # zone-to-zone, for multi-stop legs

    for a, b in pairs:
        _, dist_m, _ = astar_path(graph, node_of[a], node_of[b])
        distances[(a, b)] = dist_m
        times_minutes[(a, b)] = (dist_m / 1000) / AVG_SPEED_KMPH * 60

    _save_cache(distances, times_minutes)
    return distances, times_minutes
