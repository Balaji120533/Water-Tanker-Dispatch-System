"""
Loads the real Chennai drive-network road graph via OSMnx, bounded to a box
covering our 15 zones + 5 source stations (not the whole metro region). Caches to disk as GraphML so repeated runs/tests don't re-hit
OpenStreetMap every time.
"""

from __future__ import annotations
import os
import osmnx as ox
import networkx as nx
from zones_data import BBOX

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
CACHE_PATH = os.path.join(CACHE_DIR, "chennai_zones_drive.graphml")


def load_graph(force_refresh: bool = False) -> nx.MultiDiGraph:
    """
    Return the bounded Chennai drive-network graph, loading from disk cache
    if present, otherwise fetching from OSM and caching the result.
    """
    if not force_refresh and os.path.exists(CACHE_PATH):
        return ox.load_graphml(CACHE_PATH)

    os.makedirs(CACHE_DIR, exist_ok=True)
    north, south, east, west = BBOX
    # osmnx >= 2.0 takes bbox as (left, bottom, right, top)
    graph = ox.graph_from_bbox((west, south, east, north), network_type="drive")
    ox.save_graphml(graph, CACHE_PATH)
    return graph


def nearest_node(graph: nx.MultiDiGraph, lat: float, lon: float):
    """Find the graph node closest to a given (lat, lon) point."""
    return ox.distance.nearest_nodes(graph, X=lon, Y=lat)
