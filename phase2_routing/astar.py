"""
Custom A* search with a haversine-distance heuristic, over the real Chennai
road graph. Written from scratch (not NetworkX's shortest_path) so this
implementation can be presented and defended directly.
"""

from __future__ import annotations
import heapq
import math


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Great-circle distance between two (lat, lon) points, in meters.
    This is the heuristic function h(n) for A*: straight-line distance is
    always <= actual road distance (roads never take a shorter path than a
    straight line), so it is ADMISSIBLE — it never overestimates the true
    cost to the goal, which is what guarantees A* finds an optimal path.
    """
    R = 6_371_000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _node_latlon(graph, node):
    data = graph.nodes[node]
    return data["y"], data["x"]  # OSMnx stores lat as 'y', lon as 'x'


def astar_path(graph, start, goal):
    """
    Standard A* over a NetworkX MultiDiGraph. Edge cost is road segment
    length in meters (edge attribute 'length', as stored by OSMnx).

    Returns (path_as_list_of_nodes, total_distance_meters, nodes_expanded).
    Returns (None, float('inf'), nodes_expanded) if no path exists.
    """
    goal_lat, goal_lon = _node_latlon(graph, goal)

    # Priority queue entries: (f_score, tie_breaker, node)
    # tie_breaker avoids comparing nodes directly when f_scores are equal.
    counter = 0
    open_heap = [(0, counter, start)]
    came_from: dict = {}

    g_score = {start: 0.0}
    nodes_expanded = 0
    visited = set()

    while open_heap:
        _, _, current = heapq.heappop(open_heap)

        if current in visited:
            continue
        visited.add(current)
        nodes_expanded += 1

        if current == goal:
            return _reconstruct_path(came_from, current), g_score[current], nodes_expanded

        for neighbor in graph.successors(current):
            # A MultiDiGraph can have multiple parallel edges; use the
            # shortest one between this pair.
            edge_data = graph.get_edge_data(current, neighbor)
            edge_length = min(d.get("length", float("inf")) for d in edge_data.values())

            tentative_g = g_score[current] + edge_length

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                n_lat, n_lon = _node_latlon(graph, neighbor)
                h = haversine_meters(n_lat, n_lon, goal_lat, goal_lon)
                f = tentative_g + h
                counter += 1
                heapq.heappush(open_heap, (f, counter, neighbor))

    return None, float("inf"), nodes_expanded


def _reconstruct_path(came_from: dict, current) -> list:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
