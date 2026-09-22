import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from problem import build_problem, Tanker, Zone
from constraints import apply_capacity_constraint, zone_not_oversupplied_ok
from ac3 import ac3
from solver import solve


def test_rejects_delivery_to_an_already_covered_zone():
    # royapuram needs 6000L; T1 (9000L) already covers it, so a second
    # delivery is pure surplus.
    problem = build_problem()
    assignment = {("T1", 0): "royapuram"}
    assert zone_not_oversupplied_ok(problem, assignment, "T2", 1, "royapuram") is False


def test_allows_second_delivery_when_one_tanker_cannot_cover_need():
    # teynampet needs 10000L; a single 9000L tanker leaves 1000L short, so
    # a second delivery is legitimate rather than waste.
    problem = build_problem()
    assignment = {("T1", 0): "teynampet"}  # T1 is 9000L
    assert zone_not_oversupplied_ok(problem, assignment, "T2", 1, "teynampet") is True


def test_rejects_third_delivery_once_need_is_covered():
    # Two 9000L tankers = 18000L, well past teynampet's 10000L need.
    problem = build_problem()
    assignment = {("T1", 0): "teynampet", ("T2", 1): "teynampet"}
    assert zone_not_oversupplied_ok(problem, assignment, "T3", 2, "teynampet") is False


def test_idle_is_always_allowed():
    problem = build_problem()
    assignment = {("T1", 0): "royapuram"}
    assert zone_not_oversupplied_ok(problem, assignment, "T2", 1, None) is True


def test_single_large_tanker_covers_high_need_alone():
    # T4 is 12000L, which covers teynampet's 10000L on its own -- so a
    # second delivery after it must be rejected.
    problem = build_problem()
    assignment = {("T4", 0): "teynampet"}
    assert zone_not_oversupplied_ok(problem, assignment, "T1", 1, "teynampet") is False


def test_solver_no_longer_parks_one_zone_in_every_slot():
    # The bug this constraint fixes: previously the solver assigned
    # teynampet to all three used slots while 7 entitled zones got nothing.
    problem = build_problem()
    apply_capacity_constraint(problem)
    ac3(problem)
    solution, _ = solve(problem, "mrv+degree", "lcv")

    assert solution is not None
    assigned = [v for v in solution.values() if v is not None]
    assert len(set(assigned)) > 1, f"only one distinct zone served: {assigned}"


def test_solver_never_oversupplies_any_zone():
    problem = build_problem()
    apply_capacity_constraint(problem)
    ac3(problem)
    solution, _ = solve(problem, "mrv+degree", "lcv")
    assert solution is not None

    supplied = {}
    for (tanker_id, _slot), zone_name in solution.items():
        if zone_name is None:
            continue
        supplied.setdefault(zone_name, []).append(problem.tanker_by_id(tanker_id).capacity_liters)

    for zone_name, caps in supplied.items():
        need = problem.zone_by_name(zone_name).need_liters
        # Dropping any single delivery must leave the zone short -- i.e.
        # no delivery in the schedule was redundant.
        for i in range(len(caps)):
            without_one = sum(caps) - caps[i]
            assert without_one < need, (
                f"{zone_name}: delivery {i} was redundant "
                f"(need {need}, others already supply {without_one})"
            )
