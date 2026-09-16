import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "phase1_csp"))

from problem import build_problem
from constraints import apply_capacity_constraint
from ac3 import ac3
from solver import solve

from min_conflicts import repair, total_conflicts, conflicted_variables
from disruptions import tanker_breakdown, urgent_request


def _solved_problem():
    problem = build_problem()
    apply_capacity_constraint(problem)
    ac3(problem)
    solution, _ = solve(problem, "mrv+degree", "lcv")
    return problem, solution


def test_valid_schedule_has_zero_conflicts():
    problem, solution = _solved_problem()
    assert total_conflicts(problem, solution) == 0
    assert conflicted_variables(problem, solution) == []


def test_tanker_breakdown_creates_conflicts_when_it_had_deliveries():
    problem, solution = _solved_problem()
    # find a tanker that actually has at least one delivery in the solution
    busy_tanker = next(
        t.id for t in problem.tankers
        if any(solution[(t.id, s)] is not None for s in range(problem.num_slots))
    )
    broken = tanker_breakdown(problem, solution, busy_tanker)
    assert total_conflicts(problem, broken) > 0


def test_repair_restores_zero_conflicts_after_breakdown():
    problem, solution = _solved_problem()
    busy_tanker = next(
        t.id for t in problem.tankers
        if any(solution[(t.id, s)] is not None for s in range(problem.num_slots))
    )
    broken = tanker_breakdown(problem, solution, busy_tanker)

    repaired, diff, steps = repair(problem, broken, seed=1)

    assert repaired is not None
    assert total_conflicts(problem, repaired) == 0


def test_repair_never_reassigns_broken_tanker_to_a_delivery():
    problem, solution = _solved_problem()
    busy_tanker = next(
        t.id for t in problem.tankers
        if any(solution[(t.id, s)] is not None for s in range(problem.num_slots))
    )
    broken = tanker_breakdown(problem, solution, busy_tanker)
    repaired, diff, steps = repair(problem, broken, seed=1)

    for slot in range(problem.num_slots):
        assert repaired[(busy_tanker, slot)] is None


def test_repair_diff_is_smaller_than_full_reassignment():
    problem, solution = _solved_problem()
    busy_tanker = next(
        t.id for t in problem.tankers
        if any(solution[(t.id, s)] is not None for s in range(problem.num_slots))
    )
    broken = tanker_breakdown(problem, solution, busy_tanker)
    repaired, diff, steps = repair(problem, broken, seed=1)

    # diff should touch only a small number of variables, not the whole schedule
    assert len(diff) < len(problem.variables)


def test_urgent_request_gets_scheduled_somewhere_after_repair():
    problem, solution = _solved_problem()
    # pick a zone name NOT already in the solution
    scheduled_zones = {v for v in solution.values() if v is not None}
    unscheduled = [z.name for z in problem.zones if z.name not in scheduled_zones]
    assert unscheduled, "test fixture assumption: at least one entitled zone is unscheduled"
    urgent_zone = unscheduled[0]

    broken = urgent_request(problem, solution, urgent_zone)
    must_serve = frozenset({urgent_zone})
    repaired, diff, steps = repair(problem, broken, seed=1, must_serve=must_serve)

    assert repaired is not None
    assert total_conflicts(problem, repaired, must_serve) == 0, repaired
    assert urgent_zone in repaired.values(), repaired
