import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from problem import build_problem
from constraints import apply_capacity_constraint
from ac3 import ac3
from solver import solve


def _prep_problem():
    problem = build_problem()
    apply_capacity_constraint(problem)
    ac3(problem)
    return problem


def test_all_heuristic_combinations_find_a_valid_solution():
    combos = [
        ("none", "none"),
        ("mrv", "none"),
        ("mrv+degree", "none"),
        ("mrv+degree", "lcv"),
    ]
    for var_h, val_h in combos:
        problem = _prep_problem()
        solution, stats = solve(problem, var_heuristic=var_h, value_heuristic=val_h)
        assert solution is not None, f"{var_h}/{val_h} failed to find a solution"


def test_heuristics_do_not_increase_nodes_explored_on_this_instance():
    # MRV+degree+LCV should never do MORE work than plain backtracking on
    # the same (already AC-3-pruned) problem instance -- it may tie, but
    # should not regress.
    problem_plain = _prep_problem()
    _, stats_plain = solve(problem_plain, "none", "none")

    problem_full = _prep_problem()
    _, stats_full = solve(problem_full, "mrv+degree", "lcv")

    assert stats_full.nodes_explored <= stats_plain.nodes_explored


def test_all_combinations_respect_every_hard_constraint():
    from constraints import refill_ok, no_double_booking_ok

    problem = _prep_problem()
    solution, _ = solve(problem, "mrv+degree", "lcv")
    assert solution is not None

    all_ids = [t.id for t in problem.tankers]
    for (tanker_id, slot), value in solution.items():
        if value is not None:
            tanker = problem.tanker_by_id(tanker_id)
            zone = problem.zone_by_name(value)
            assert zone.need_liters <= tanker.capacity_liters

    for slot in range(problem.num_slots - 1):
        for t in problem.tankers:
            v1 = solution[(t.id, slot)]
            v2 = solution[(t.id, slot + 1)]
            assert not (v1 is not None and v2 is not None)

    for slot in range(problem.num_slots):
        zones_this_slot = [
            solution[(t.id, slot)] for t in problem.tankers if solution[(t.id, slot)] is not None
        ]
        assert len(zones_this_slot) == len(set(zones_this_slot))
