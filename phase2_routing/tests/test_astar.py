import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import networkx as nx
from graph_loader import load_graph, nearest_node
from zones_data import ZONE_COORDS, SOURCE_STATIONS
from astar import astar_path, haversine_meters

GRAPH = load_graph()


def test_haversine_zero_for_identical_points():
    assert haversine_meters(13.05, 80.25, 13.05, 80.25) == 0


def test_haversine_known_distance_order_of_magnitude():
    # thiruvotriyur to perungudi is roughly north-to-south across the city,
    # on the order of 20-25 km as the crow flies.
    lat1, lon1 = ZONE_COORDS["thiruvotriyur"]
    lat2, lon2 = ZONE_COORDS["perungudi"]
    dist = haversine_meters(lat1, lon1, lat2, lon2)
    assert 15_000 < dist < 30_000


def test_astar_finds_a_path_between_station_and_zone():
    lat1, lon1 = SOURCE_STATIONS["station_c"]
    lat2, lon2 = ZONE_COORDS["teynampet"]
    start = nearest_node(GRAPH, lat1, lon1)
    goal = nearest_node(GRAPH, lat2, lon2)

    path, distance, nodes_expanded = astar_path(GRAPH, start, goal)

    assert path is not None
    assert path[0] == start
    assert path[-1] == goal
    assert distance > 0
    assert nodes_expanded > 0


def test_astar_distance_matches_networkx_dijkstra():
    # A* with an admissible heuristic must find the SAME optimal cost as
    # plain Dijkstra/shortest_path (which is what NetworkX's built-in uses)
    # -- this is the correctness check for the custom implementation.
    lat1, lon1 = SOURCE_STATIONS["station_a"]
    lat2, lon2 = ZONE_COORDS["manali"]
    start = nearest_node(GRAPH, lat1, lon1)
    goal = nearest_node(GRAPH, lat2, lon2)

    _, astar_distance, _ = astar_path(GRAPH, start, goal)
    nx_distance = nx.shortest_path_length(GRAPH, start, goal, weight="length")

    assert abs(astar_distance - nx_distance) < 1.0  # meters, allow float slop


def test_astar_returns_no_path_for_unreachable_disconnected_node():
    # Construct a trivial disconnected graph to test the no-path branch
    # without depending on real map disconnection (which may not exist).
    g = nx.MultiDiGraph()
    g.add_node(1, y=13.0, x=80.0)
    g.add_node(2, y=13.01, x=80.01)
    # no edge between them
    path, distance, nodes_expanded = astar_path(g, 1, 2)
    assert path is None
    assert distance == float("inf")
