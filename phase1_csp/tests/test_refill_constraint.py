import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from problem import build_problem
from constraints import apply_capacity_constraint, refill_ok
from solver import solve


def test_refill_ok_rejects_back_to_back_deliveries():
    assignment = {("T1", 0): "royapuram"}
    # T1 already delivered in slot 0 -> slot 1 must be idle, not another delivery
    assert refill_ok(assignment, "T1", 1, "manali", num_slots=3) is False


def test_refill_ok_allows_idle_after_delivery():
    assignment = {("T1", 0): "royapuram"}
    assert refill_ok(assignment, "T1", 1, None, num_slots=3) is True


def test_refill_ok_allows_delivery_after_idle():
    assignment = {("T1", 0): None}
    assert refill_ok(assignment, "T1", 1, "royapuram", num_slots=3) is True


def test_refill_ok_checks_forward_neighbor_too():
    # slot 2 already assigned a delivery; proposing a delivery in slot 1
    # must be rejected even though slot 1 is being assigned "backwards"
    # relative to slot 2.
    assignment = {("T1", 2): "royapuram"}
    assert refill_ok(assignment, "T1", 1, "manali", num_slots=3) is False


def test_solver_never_double_delivers_consecutive_slots():
    problem = build_problem()
    apply_capacity_constraint(problem)
    solution, stats = solve(problem)

    assert solution is not None
    for t in problem.tankers:
        for slot in range(problem.num_slots - 1):
            v1 = solution[(t.id, slot)]
            v2 = solution[(t.id, slot + 1)]
            assert not (v1 is not None and v2 is not None), (
                f"{t.id} delivered in consecutive slots {slot} and {slot + 1}"
            )
