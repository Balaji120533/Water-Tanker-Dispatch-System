"""
Sequences a tanker's deliveries for the day: given a set of zones one
tanker must visit (each visit starting and ending at a source station,
since Phase 1's refill constraint means every delivery is followed by a
return-to-station), find an ordering that minimizes total travel time.

This is a small Traveling-Salesman-shaped optimization. Exact search over
all orderings is fine at tiny sizes but we deliberately implement local
search (hill climbing, then simulated annealing) since that's the Unit II
technique this phase is meant to demonstrate, and it's what would scale if
a tanker's zone count grew.
"""

from __future__ import annotations
import math
import random


def route_cost(times_minutes: dict, station: str, zone_order: list[str]) -> float:
    """
    Total travel time for station -> zone1 -> station -> zone2 -> station
    -> ... -> station: each delivery is an independent round trip from the
    station (Phase 1's refill constraint). Under this model cost is simply
    the sum of round-trip times, so ORDER does not change the total -- see
    multi_stop_leg_cost() below for the model where order actually matters.
    Kept here because Phase 1's committed schedule still uses this model;
    this function scores it faithfully rather than silently switching
    models.
    """
    total = 0.0
    for zone in zone_order:
        total += times_minutes[(station, zone)] + times_minutes[(zone, station)]
    return total


def multi_stop_leg_cost(times_minutes: dict, zone_zone_times: dict, station: str, zone_order: list[str]) -> float:
    """
    Total travel time for ONE multi-stop leg: station -> zone_order[0] ->
    zone_order[1] -> ... -> zone_order[-1] -> station. Used when a single
    tanker visits several NEARBY zones back-to-back before returning to
    refill (their combined need still fits its capacity) -- here the visit
    ORDER genuinely changes total distance, which is what makes hill
    climbing / simulated annealing meaningful (this is the classic
    traveling-salesman-shaped sub-problem: minimize a Hamiltonian path's
    length by reordering its stops).
    """
    if not zone_order:
        return 0.0
    total = times_minutes[(station, zone_order[0])]
    for a, b in zip(zone_order, zone_order[1:]):
        total += zone_zone_times[(a, b)]
    total += times_minutes[(zone_order[-1], station)]
    return total


def _swap_neighbors(order: list[str]):
    """Generate all orderings reachable by swapping two positions."""
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            neighbor = list(order)
            neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
            yield neighbor


def hill_climb(cost_fn, zone_order: list[str]):
    """
    Steepest-ascent (steepest-descent, since we minimize) hill climbing:
    repeatedly move to the best neighboring ordering (one swap away) as
    long as it strictly improves cost. Stops at a local minimum.

    cost_fn: callable(order) -> float, so this same search works for both
    route_cost (order-invariant) and multi_stop_leg_cost (order matters).

    Returns (best_order, best_cost, iterations).
    """
    current = list(zone_order)
    current_cost = cost_fn(current)
    iterations = 0

    while True:
        iterations += 1
        best_neighbor = None
        best_neighbor_cost = current_cost

        for neighbor in _swap_neighbors(current):
            cost = cost_fn(neighbor)
            if cost < best_neighbor_cost:
                best_neighbor = neighbor
                best_neighbor_cost = cost

        if best_neighbor is None:
            break  # local minimum -- no swap improves

        current, current_cost = best_neighbor, best_neighbor_cost

    return current, current_cost, iterations


def simulated_annealing(
    cost_fn,
    zone_order: list[str],
    initial_temp: float = 100.0,
    cooling_rate: float = 0.95,
    min_temp: float = 0.1,
    steps_per_temp: int = 20,
    seed: int | None = None,
):
    """
    Simulated annealing: like hill climbing, but occasionally accepts a
    WORSE neighbor (with probability that shrinks as "temperature" cools),
    so it can escape local minima that hill climbing gets stuck in.

    cost_fn: callable(order) -> float (see hill_climb).

    Returns (best_order, best_cost, iterations).
    """
    rng = random.Random(seed)

    current = list(zone_order)
    current_cost = cost_fn(current)
    best, best_cost = list(current), current_cost

    temp = initial_temp
    iterations = 0

    while temp > min_temp:
        for _ in range(steps_per_temp):
            iterations += 1
            neighbor = list(current)
            if len(neighbor) >= 2:
                i, j = rng.sample(range(len(neighbor)), 2)
                neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
            neighbor_cost = cost_fn(neighbor)

            delta = neighbor_cost - current_cost
            if delta < 0 or rng.random() < math.exp(-delta / temp):
                current, current_cost = neighbor, neighbor_cost
                if current_cost < best_cost:
                    best, best_cost = list(current), current_cost

        temp *= cooling_rate

    return best, best_cost, iterations
