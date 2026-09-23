import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import osmnx as ox
from graph_loader import load_graph
from zones_data import SOURCE_STATIONS
from astar import astar_path
from dynamic_route import RoutePlanner

GRAPH = load_graph()
PLANNER = RoutePlanner(GRAPH, SOURCE_STATIONS)

# Real localities from data/metrowater/localities.csv, spread across the city.
PLACES = {
    "Arumbakkam": (13.074371, 80.208131),
    "Vadapalani": (13.050298, 80.21183),
    "Velachery": (12.980165, 80.222851),
    "Kolathur": (13.123655, 80.212885),
    "Ennore": (13.225826, 80.324355),
}


def _brute_force(lat, lon):
    goal = ox.distance.nearest_nodes(GRAPH, X=lon, Y=lat)
    best = None
    for name, node in PLANNER.station_node.items():
        path, dist, _ = astar_path(GRAPH, node, goal)
        if path is not None and (best is None or dist < best[1]):
            best = (name, dist)
    return best


@pytest.mark.parametrize("place", PLACES)
def test_early_stop_finds_the_true_nearest_filling_point(place):
    # The cut-off (stop once straight-line distance exceeds the best road
    # distance) must never change the answer versus trying all 22.
    lat, lon = PLACES[place]
    got = PLANNER.nearest_filling_point(lat, lon)
    name, dist = _brute_force(lat, lon)
    assert got["station"] == name
    assert abs(got["distance_m"] - dist) < 1.0


def test_early_stop_searches_fewer_than_all_filling_points():
    lat, lon = PLACES["Arumbakkam"]
    got = PLANNER.nearest_filling_point(lat, lon)
    assert got["filling_points_searched"] < got["filling_points_total"]


def test_route_is_a_drawable_road_polyline():
    lat, lon = PLACES["Arumbakkam"]
    got = PLANNER.nearest_filling_point(lat, lon)
    assert len(got["coords"]) > 2
    # Ends at the road node nearest the reported place (within ~300 m).
    end_lat, end_lon = got["coords"][-1]
    assert abs(end_lat - lat) < 0.003 and abs(end_lon - lon) < 0.003
