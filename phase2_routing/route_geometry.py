"""
Pre-computes the actual road-path GEOMETRY (lat/lon polylines) for every
source-station -> zone pair, using our custom A* from astar.py.

travel_times.py caches distances/times but not the path itself. The driver
view needs the real polyline to draw the route on a map, and loading the
~57MB road graph inside a web request would be far too slow -- so this
module computes every station->zone path once and caches the coordinate
lists to JSON, which the API can then serve instantly.
"""

from __future__ import annotations
import json
import os
from graph_loader import load_graph, nearest_node
from zones_data import ZONE_COORDS, SOURCE_STATIONS
from astar import astar_path

CACHE_PATH = os.path.join(os.path.dirname(__file__), "cache", "route_geometry.json")


def _key(station: str, zone: str) -> str:
    return f"{station}|{zone}"


def _edge_shape(graph, u, v) -> list[list[float]]:
    """
    Return the true road shape between two adjacent nodes as [[lat, lon], ...],
    EXCLUDING the start node (callers append it once, so joining legs doesn't
    duplicate points).

    OSMnx only places graph nodes at intersections. A curved road between two
    intersections is stored as a LineString on the edge's `geometry`
    attribute -- if you draw node-to-node you get a straight chord that cuts
    corners and appears to run through buildings. Only edges that are
    genuinely straight omit `geometry`.
    """
    data = graph.get_edge_data(u, v)
    if not data:
        return [[graph.nodes[v]["y"], graph.nodes[v]["x"]]]

    # Parallel edges are possible; follow the shortest, matching what A* costed.
    best = min(data.values(), key=lambda d: d.get("length", float("inf")))
    geom = best.get("geometry")

    if geom is None:
        return [[graph.nodes[v]["y"], graph.nodes[v]["x"]]]

    # LineString stores (lon, lat); Leaflet wants [lat, lon].
    pts = [[lat, lon] for lon, lat in geom.coords]

    # The stored LineString may run either direction; orient it so it ends
    # at v, otherwise the drawn route doubles back on itself.
    v_lat, v_lon = graph.nodes[v]["y"], graph.nodes[v]["x"]
    if pts and _dist2(pts[0], (v_lat, v_lon)) < _dist2(pts[-1], (v_lat, v_lon)):
        pts.reverse()

    return pts[1:] if len(pts) > 1 else pts


def _dist2(a, b) -> float:
    """Squared planar distance -- only used to compare which end is closer."""
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _path_to_coords(graph, node_path: list) -> list[list[float]]:
    """Expand a node path into the full road-following polyline."""
    if not node_path:
        return []
    start = node_path[0]
    coords = [[graph.nodes[start]["y"], graph.nodes[start]["x"]]]
    for u, v in zip(node_path, node_path[1:]):
        coords.extend(_edge_shape(graph, u, v))
    return coords


def build_route_geometry(force_refresh: bool = False) -> dict:
    """
    Returns {"station|zone": {"coords": [[lat, lon], ...], "distance_m": float}}
    for every station->zone pair. Cached to disk after the first run.
    """
    if not force_refresh and os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    graph = load_graph()
    all_points = {**SOURCE_STATIONS, **ZONE_COORDS}
    node_of = {name: nearest_node(graph, lat, lon) for name, (lat, lon) in all_points.items()}

    routes = {}
    for station in SOURCE_STATIONS:
        for zone in ZONE_COORDS:
            path, dist_m, _ = astar_path(graph, node_of[station], node_of[zone])
            if path is None:
                continue
            coords = _path_to_coords(graph, path)
            routes[_key(station, zone)] = {"coords": coords, "distance_m": dist_m}

    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(routes, f)
    return routes


def nearest_station_to_zone(routes: dict, zone: str) -> tuple[str, dict]:
    """
    Pick the source station with the SHORTEST real road distance to this
    zone (not straight-line distance) -- the station a driver would
    actually refill at before serving it.
    """
    best_station, best_route = None, None
    for station in SOURCE_STATIONS:
        route = routes.get(_key(station, zone))
        if route is None:
            continue
        if best_route is None or route["distance_m"] < best_route["distance_m"]:
            best_station, best_route = station, route
    return best_station, best_route
