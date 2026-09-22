import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from problem import build_problem
from constraints import apply_capacity_constraint


def test_small_tanker_may_still_be_sent_to_a_large_zone():
    # A 9000L tanker cannot cover a 10000L zone ALONE, but two deliveries
    # can -- constraint (d) exists precisely for that. Pruning the zone out
    # of the small tanker's domain here would make it unservable whenever
    # the large tankers are busy, so (a) must NOT prune on full need.
    problem = build_problem()
    apply_capacity_constraint(problem)

    for (tanker_id, slot), domain in problem.domains.items():
        tanker = problem.tanker_by_id(tanker_id)
        if tanker.capacity_liters < 10000:
            assert "teynampet" in domain
            assert "tondiarpet" in domain


def test_large_zone_is_only_satisfied_once_deliveries_cover_its_need():
    # The volume rule that replaced the old pruning: one 9000L delivery
    # leaves a 10000L zone short; a second one covers it.
    from soft_constraints import schedule_score

    problem = build_problem()
    one_delivery = {("T1", 0): "teynampet"}          # 9000L against 10000L need
    two_deliveries = {("T1", 0): "teynampet", ("T2", 1): "teynampet"}  # 18000L

    assert schedule_score(problem, one_delivery) == 0
    assert schedule_score(problem, two_deliveries) > 0


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
