import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from functools import partial

from sequencing import route_cost, multi_stop_leg_cost, hill_climb, simulated_annealing

# Small synthetic travel-time table for isolated, fast tests (no graph dependency).
TIMES = {
    ("station", "z1"): 10, ("z1", "station"): 10,
    ("station", "z2"): 5, ("z2", "station"): 5,
    ("station", "z3"): 20, ("z3", "station"): 20,
}

# Zone-to-zone times for the multi-stop leg model, deliberately asymmetric
# in effect: visiting in a bad order should cost noticeably more.
ZZ_TIMES = {
    ("z1", "z2"): 3, ("z2", "z1"): 3,
    ("z1", "z3"): 25, ("z3", "z1"): 25,
    ("z2", "z3"): 22, ("z3", "z2"): 22,
}


def test_route_cost_is_order_invariant_under_return_to_station_model():
    # Because every delivery round-trips back to the station (Phase 1's
    # refill constraint), total cost is just the sum of round trips --
    # order genuinely does not change the total under THIS model. This is
    # an honest, examinable finding: local search over THIS objective
    # converges immediately since every neighbor ties. See
    # multi_stop_leg_cost tests below for the model where order matters.
    cost_a = route_cost(TIMES, "station", ["z1", "z2", "z3"])
    cost_b = route_cost(TIMES, "station", ["z3", "z1", "z2"])
    assert cost_a == cost_b


def test_multi_stop_leg_cost_is_order_dependent():
    # z1 is close to the station and to z2, but z3 is far from everything
    # except close-ish to nothing -- visiting z3 in the middle should cost
    # more than visiting it last.
    cost_good = multi_stop_leg_cost(TIMES, ZZ_TIMES, "station", ["z1", "z2", "z3"])
    cost_bad = multi_stop_leg_cost(TIMES, ZZ_TIMES, "station", ["z3", "z1", "z2"])
    assert cost_good != cost_bad


def test_hill_climb_returns_a_valid_permutation():
    cost_fn = partial(route_cost, TIMES, "station")
    order, cost, iterations = hill_climb(cost_fn, ["z1", "z2", "z3"])
    assert sorted(order) == sorted(["z1", "z2", "z3"])
    assert cost == cost_fn(order)


def test_hill_climb_terminates():
    cost_fn = partial(route_cost, TIMES, "station")
    order, cost, iterations = hill_climb(cost_fn, ["z3", "z2", "z1"])
    assert iterations >= 1
    assert iterations < 100  # sanity bound -- must not loop forever


def test_hill_climb_finds_optimal_order_on_multi_stop_leg():
    cost_fn = partial(multi_stop_leg_cost, TIMES, ZZ_TIMES, "station")
    # brute force the true optimum over all 6 permutations of 3 zones
    from itertools import permutations
    true_best = min(cost_fn(list(p)) for p in permutations(["z1", "z2", "z3"]))

    order, cost, iterations = hill_climb(cost_fn, ["z3", "z1", "z2"])  # start from a bad order
    assert abs(cost - true_best) < 1e-9


def test_simulated_annealing_returns_a_valid_permutation():
    cost_fn = partial(route_cost, TIMES, "station")
    order, cost, iterations = simulated_annealing(cost_fn, ["z1", "z2", "z3"], seed=1)
    assert sorted(order) == sorted(["z1", "z2", "z3"])
    assert cost == cost_fn(order)


def test_simulated_annealing_never_beats_true_optimum_on_multi_stop_leg():
    cost_fn = partial(multi_stop_leg_cost, TIMES, ZZ_TIMES, "station")
    from itertools import permutations
    true_best = min(cost_fn(list(p)) for p in permutations(["z1", "z2", "z3"]))

    order, cost, _ = simulated_annealing(cost_fn, ["z3", "z1", "z2"], seed=1)
    assert cost >= true_best - 1e-9
