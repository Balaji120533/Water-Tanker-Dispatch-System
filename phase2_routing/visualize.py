"""
Simple map output so routes can be eyeballed for correctness (CLAUDE.md
Phase 2 deliverable). Draws the real road-network path (from our A*, not a
straight line) for a multi-stop leg, plus markers for stations and zones.

Usage: python visualize.py
Produces: route_map.html (open in a browser)
"""

from __future__ import annotations
import folium
from functools import partial
from graph_loader import load_graph, nearest_node
from zones_data import SOURCE_STATIONS, ZONE_COORDS
from astar import astar_path
from travel_times import build_travel_time_matrix
from sequencing import multi_stop_leg_cost, hill_climb
from route_geometry import _path_to_coords


def _node_path_to_latlon(graph, node_path):
    # Expands each edge into its true road shape -- node-to-node lines
    # would cut corners, since OSMnx only places nodes at intersections.
    return _path_to_coords(graph, node_path)


def main():
    graph = load_graph()
    distances, times = build_travel_time_matrix(graph)

    station = "fp_kk_nagar"  # the filling point serving Kodambakkam
    stop_order_start = ["alandur", "teynampet", "kodambakkam"]
    cost_fn = partial(multi_stop_leg_cost, times, times, station)
    optimized_order, cost, _ = hill_climb(cost_fn, stop_order_start)

    full_stops = [station] + optimized_order + [station]
    center_lat, center_lon = SOURCE_STATIONS[station]
    # Default OSM tile server actively blocks unauthenticated/automated
    # access ("Access blocked" 403 tiles) -- CartoDB's free tile set has no
    # such restriction and is the standard folium fallback for this.
    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles="CartoDB positron",
    )

    # Mark every source station and zone for context.
    for name, (lat, lon) in SOURCE_STATIONS.items():
        folium.Marker(
            [lat, lon], popup=f"Source: {name}", icon=folium.Icon(color="blue", icon="tint")
        ).add_to(fmap)
    for name, (lat, lon) in ZONE_COORDS.items():
        folium.Marker(
            [lat, lon], popup=f"Zone: {name}", icon=folium.Icon(color="red", icon="home")
        ).add_to(fmap)

    # Draw the actual road-network path (from our A*) for each leg of the
    # optimized route, so the route drawn follows real streets.
    all_coords = {**SOURCE_STATIONS, **ZONE_COORDS}
    for a, b in zip(full_stops, full_stops[1:]):
        node_a = nearest_node(graph, *all_coords[a])
        node_b = nearest_node(graph, *all_coords[b])
        path, dist_m, _ = astar_path(graph, node_a, node_b)
        if path:
            latlon_path = _node_path_to_latlon(graph, path)
            folium.PolyLine(latlon_path, color="green", weight=4, opacity=0.8).add_to(fmap)

    out_path = "route_map.html"
    fmap.save(out_path)
    print(f"Route: {full_stops}")
    print(f"Total time: {cost:.1f} min")
    print(f"Map saved to {out_path}")


if __name__ == "__main__":
    main()
