"""
Route a tanker to the exact place a volunteer reported -- "Arumbakkam", not
just the centre of Zone 8 -- from whichever filling point is nearest BY
ROAD.

route_geometry.py precomputes filling-point -> zone-centre routes, which is
enough when all we know is the zone. A volunteer report names a specific
locality, so its route has to be found when the report arrives.

Finding the nearest filling point naively means one A* per filling point
(22 of them). Instead they are tried in order of straight-line distance,
and the search stops as soon as the next candidate's straight-line
distance is already longer than the best road distance found. That cut-off
is exact, not a heuristic guess, for the same reason the A* heuristic is
admissible: no road between two points is shorter than the straight line
between them, so a candidate that loses on straight-line distance cannot
win on road distance.

Pure module (Rule 4): takes a graph and coordinates, returns plain data.
"""

from __future__ import annotations
import osmnx as ox

from astar import astar_path, haversine_meters, _node_latlon
from route_geometry import _path_to_coords


class RoutePlanner:
    def __init__(self, graph, stations: dict[str, tuple[float, float]]):
        self.graph = graph
        names = list(stations)
        # Snap every filling point to the road network once, up front.
        nodes = ox.distance.nearest_nodes(
            graph, X=[stations[n][1] for n in names], Y=[stations[n][0] for n in names]
        )
        self.station_node = dict(zip(names, nodes))

    def nearest_filling_point(self, lat: float, lon: float) -> dict | None:
        """
        The filling point with the shortest road route to (lat, lon), and
        that route. Returns None only if no filling point can reach it.
        """
        goal = ox.distance.nearest_nodes(self.graph, X=lon, Y=lat)
        goal_lat, goal_lon = _node_latlon(self.graph, goal)

        # Straight-line distance between the SNAPPED nodes -- the road route
        # runs between these nodes, so this is a true lower bound on it.
        def straight_line(name):
            s_lat, s_lon = _node_latlon(self.graph, self.station_node[name])
            return haversine_meters(s_lat, s_lon, goal_lat, goal_lon)

        candidates = sorted(self.station_node, key=straight_line)

        best = None
        searched = 0
        for name in candidates:
            if best is not None and straight_line(name) >= best["distance_m"]:
                break  # every remaining candidate is at least this far by road
            path, dist_m, _ = astar_path(self.graph, self.station_node[name], goal)
            searched += 1
            if path is not None and (best is None or dist_m < best["distance_m"]):
                best = {"station": name, "distance_m": dist_m, "path": path}

        if best is None:
            return None
        return {
            "station": best["station"],
            "distance_m": best["distance_m"],
            "coords": _path_to_coords(self.graph, best["path"]),
            "filling_points_searched": searched,
            "filling_points_total": len(candidates),
        }
