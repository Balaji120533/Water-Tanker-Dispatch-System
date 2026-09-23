"""
Terminal demo for Phase 2: real A* routing + route sequencing.

Usage: python demo.py
"""

from __future__ import annotations
from functools import partial
from travel_times import build_travel_time_matrix
from sequencing import route_cost, multi_stop_leg_cost, hill_climb, simulated_annealing
from zones_data import SOURCE_STATIONS, ZONE_COORDS


def main():
    print("Loading travel time matrix (cached after first run)...")
    distances, times = build_travel_time_matrix()

    station = "fp_kk_nagar"  # the filling point serving Kodambakkam
    print(f"\n=== Single-delivery model (each visit round-trips to {station}) ===")
    zones = ["teynampet", "kodambakkam", "alandur"]
    cost_1 = route_cost(times, station, zones)
    cost_2 = route_cost(times, station, list(reversed(zones)))
    print(f"Order {zones}: {cost_1:.1f} min")
    print(f"Order {list(reversed(zones))}: {cost_2:.1f} min")
    print("(Equal, as expected -- order-invariant under the round-trip-per-delivery model.)")

    print(f"\n=== Multi-stop leg model (one trip visiting all three before returning) ===")
    cost_fn = partial(multi_stop_leg_cost, times, times, station)
    bad_order = ["alandur", "teynampet", "kodambakkam"]
    print(f"Starting order {bad_order}: {cost_fn(bad_order):.1f} min")

    hc_order, hc_cost, hc_iters = hill_climb(cost_fn, bad_order)
    print(f"Hill climbing  -> {hc_order}: {hc_cost:.1f} min ({hc_iters} iterations)")

    sa_order, sa_cost, sa_iters = simulated_annealing(cost_fn, bad_order, seed=1)
    print(f"Sim. annealing -> {sa_order}: {sa_cost:.1f} min ({sa_iters} iterations)")


if __name__ == "__main__":
    main()
