import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from problem import build_problem
from constraints import apply_capacity_constraint, no_double_booking_ok
from solver import solve


def test_rejects_same_zone_same_slot_different_tanker():
    assignment = {("T1", 0): "royapuram"}
    all_ids = ["T1", "T2", "T3", "T4", "T5"]
    assert no_double_booking_ok(assignment, "T2", 0, "royapuram", all_ids) is False


def test_allows_same_zone_different_slot():
    assignment = {("T1", 0): "royapuram"}
    all_ids = ["T1", "T2", "T3", "T4", "T5"]
    assert no_double_booking_ok(assignment, "T2", 1, "royapuram", all_ids) is True


def test_allows_different_zone_same_slot():
    assignment = {("T1", 0): "royapuram"}
    all_ids = ["T1", "T2", "T3", "T4", "T5"]
    assert no_double_booking_ok(assignment, "T2", 0, "manali", all_ids) is True


def test_idle_never_conflicts():
    assignment = {("T1", 0): "royapuram"}
    all_ids = ["T1", "T2", "T3", "T4", "T5"]
    assert no_double_booking_ok(assignment, "T2", 0, None, all_ids) is True


def test_solver_never_sends_two_tankers_to_same_zone_same_slot():
    problem = build_problem()
    apply_capacity_constraint(problem)
    solution, stats = solve(problem)

    assert solution is not None
    for slot in range(problem.num_slots):
        zones_this_slot = [
            solution[(t.id, slot)] for t in problem.tankers if solution[(t.id, slot)] is not None
        ]
        assert len(zones_this_slot) == len(set(zones_this_slot)), (
            f"slot {slot} has a duplicate zone assignment: {zones_this_slot}"
        )
