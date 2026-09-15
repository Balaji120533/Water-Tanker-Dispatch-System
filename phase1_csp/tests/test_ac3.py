import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from problem import build_problem, Tanker, Zone, CSPProblem
from constraints import apply_capacity_constraint
from ac3 import ac3, revise, build_arcs
from solver import solve


def test_ac3_returns_true_on_satisfiable_problem():
    problem = build_problem()
    apply_capacity_constraint(problem)
    assert ac3(problem) is True


def test_ac3_does_not_break_solvability():
    problem = build_problem()
    apply_capacity_constraint(problem)
    ac3(problem)
    solution, stats = solve(problem)
    assert solution is not None


def test_ac3_never_removes_none_from_any_domain():
    # idle is always a safe value under refill/no-double-booking, so AC-3
    # must never prune it away.
    problem = build_problem()
    apply_capacity_constraint(problem)
    ac3(problem)
    for domain in problem.domains.values():
        assert None in domain


def test_ac3_detects_unsatisfiable_problem():
    # Build a deliberately impossible problem: 1 tanker, 1 slot, but the
    # only zone needs more water than the tanker can carry, and capacity
    # pruning removes it from the domain entirely -> AC-3 still returns
    # True (an empty domain from capacity pruning is a different failure
    # mode than an AC-3-detected one) but we can verify AC-3 itself detects
    # a genuine arc-consistency wipeout using a contrived 2-slot refill trap.
    tankers = [Tanker("T1", 9000)]
    zones = [Zone("only_zone", 6000, False)]
    problem = build_problem(tankers=tankers, zones=zones, num_slots=2)
    apply_capacity_constraint(problem)
    # Force T1 slot 0's domain down to a single non-idle value so slot 1
    # is forced to idle by refill -- this is satisfiable, so instead verify
    # a real wipeout: strip idle out of slot 1's domain by hand, which no
    # legitimate constraint would do, to confirm ac3 propagates emptiness.
    problem.domains[("T1", 0)] = ["only_zone"]
    problem.domains[("T1", 1)] = ["only_zone"]  # idle removed -> impossible
    assert ac3(problem) is False


def test_revise_prunes_value_with_no_support():
    tankers = [Tanker("T1", 9000)]
    zones = [Zone("z", 6000, False)]
    problem = build_problem(tankers=tankers, zones=zones, num_slots=2)
    problem.domains[("T1", 0)] = ["z"]
    problem.domains[("T1", 1)] = ["z"]  # no idle -> "z" in slot 0 has no support
    changed = revise(problem, ("T1", 0), ("T1", 1))
    assert changed is True
    assert problem.domains[("T1", 0)] == []


def test_build_arcs_includes_both_directions():
    problem = build_problem()
    arcs = build_arcs(problem)
    arc_set = set(arcs)
    # spot check one refill pair both ways
    assert (("T1", 0), ("T1", 1)) in arc_set
    assert (("T1", 1), ("T1", 0)) in arc_set
