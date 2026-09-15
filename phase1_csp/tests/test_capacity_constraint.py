import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from problem import build_problem
from constraints import apply_capacity_constraint


def test_9000L_tanker_cannot_serve_10000L_high_priority_zone():
    problem = build_problem()
    apply_capacity_constraint(problem)

    for (tanker_id, slot), domain in problem.domains.items():
        tanker = problem.tanker_by_id(tanker_id)
        if tanker.capacity_liters < 10000:
            assert "teynampet" not in domain
            assert "tondiarpet" not in domain


def test_12000L_tanker_can_serve_every_zone():
    problem = build_problem()
    apply_capacity_constraint(problem)

    for (tanker_id, slot), domain in problem.domains.items():
        tanker = problem.tanker_by_id(tanker_id)
        if tanker.capacity_liters == 12000:
            for zone in problem.zones:
                assert zone.name in domain


def test_idle_always_remains_in_domain():
    problem = build_problem()
    apply_capacity_constraint(problem)

    for domain in problem.domains.values():
        assert None in domain


def test_normal_need_zones_available_to_every_tanker():
    problem = build_problem()
    apply_capacity_constraint(problem)

    normal_zones = {z.name for z in problem.zones if not z.is_high_priority}
    for domain in problem.domains.values():
        assert normal_zones.issubset(set(domain))
