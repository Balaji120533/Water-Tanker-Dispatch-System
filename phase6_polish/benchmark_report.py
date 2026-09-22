"""
Consolidated benchmark tables (CLAUDE.md Phase 6).

Two tables, because they answer different questions:

  A. SATISFACTION search -- how much work to find ANY schedule meeting the
     hard constraints. This is what phase1_csp/benchmark.py measures, and
     the honest finding there is that the heuristics do not reduce nodes
     on our instances: "leave every tanker idle" satisfies every hard
     constraint, so the very first path tried already succeeds and there
     is nothing for MRV/degree/LCV to prune.

  B. OPTIMISATION search -- how much work to find the BEST schedule under
     the soft constraint (serve as many entitled zones as possible, high
     priority first). Here the search cannot stop at the first valid leaf,
     so ordering and bounding genuinely matter -- and this is the solver
     the dispatcher and the fairness study actually use.

Run: python benchmark_report.py
"""

from __future__ import annotations
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase1_csp"))

from problem import build_problem, Tanker, Zone  # noqa: E402
from constraints import apply_capacity_constraint  # noqa: E402
from ac3 import ac3  # noqa: E402
from solver import solve as csp_solve  # noqa: E402
from soft_constraints import solve_best, schedule_score  # noqa: E402

REPEATS = 50


def _prepared(use_ac3: bool = True, **kwargs):
    problem = build_problem(**kwargs)
    apply_capacity_constraint(problem)
    if use_ac3:
        ac3(problem)
    return problem


def _zones_satisfied(problem, solution) -> int:
    supplied = {}
    for (tanker_id, _slot), zone_name in solution.items():
        if zone_name is None:
            continue
        supplied[zone_name] = supplied.get(zone_name, 0) + problem.tanker_by_id(tanker_id).capacity_liters
    return sum(1 for n, l in supplied.items() if l >= problem.zone_by_name(n).need_liters)


def table_a():
    print("=" * 78)
    print("TABLE A -- SATISFACTION SEARCH (first schedule meeting the hard constraints)")
    print("=" * 78)
    print("%-34s %8s %8s %12s %10s" % ("configuration", "solved", "nodes", "time (ms)", "zones met"))
    print("-" * 78)

    configs = [
        ("no AC-3, plain backtracking", False, "none", "none"),
        ("AC-3, plain backtracking", True, "none", "none"),
        ("AC-3 + MRV", True, "mrv", "none"),
        ("AC-3 + MRV + degree", True, "mrv+degree", "none"),
        ("AC-3 + MRV + degree + LCV", True, "mrv+degree", "lcv"),
    ]

    for label, use_ac3, var_h, val_h in configs:
        problem = _prepared(use_ac3=use_ac3)
        solution, stats = csp_solve(problem, var_h, val_h)

        total = 0.0
        for _ in range(REPEATS):
            p = _prepared(use_ac3=use_ac3)
            t0 = time.perf_counter()
            csp_solve(p, var_h, val_h)
            total += time.perf_counter() - t0

        met = _zones_satisfied(problem, solution) if solution else 0
        print("%-34s %8s %8d %12.4f %10d"
              % (label, bool(solution), stats.nodes_explored, (total / REPEATS) * 1000, met))

    print()
    print("Reading: node counts are identical across every configuration. An")
    print("all-idle schedule satisfies every hard constraint, so the first path")
    print("tried already succeeds and there is no dead end for MRV/degree/LCV to")
    print("avoid -- the heuristics only add bookkeeping cost here.")
    print()
    print("The 'zones met' column is the important one, and it is not a quality")
    print("ranking: satisfaction search has NO objective, so how many zones get")
    print("served is incidental to the variable/value ordering. The same solver")
    print("happens to reach 8 zones under one ordering and 3 under another, with")
    print("no mechanism preferring either. That arbitrariness -- not the node")
    print("count -- is the reason the soft constraint in Table B is needed.")


def table_b():
    print()
    print("=" * 78)
    print("TABLE B -- OPTIMISATION SEARCH (best schedule under the soft constraint)")
    print("=" * 78)
    print("%-34s %8s %8s %12s %10s" % ("instance", "score", "nodes", "time (ms)", "zones met"))
    print("-" * 78)

    instances = [
        ("real: 5 tankers, 8 zones", {}),
        ("strained: 2 tankers, 8 zones",
         {"tankers": [Tanker("T1", 9000), Tanker("T2", 9000)]}),
        ("large: 5 tankers, 8 zones, 5 slots", {"num_slots": 5}),
    ]

    for label, kwargs in instances:
        problem = _prepared(**kwargs)
        t0 = time.perf_counter()
        solution, stats, score = solve_best(problem)
        elapsed = (time.perf_counter() - t0) * 1000
        met = _zones_satisfied(problem, solution) if solution else 0
        print("%-34s %8d %8d %12.2f %10d" % (label, score, stats.nodes_explored, elapsed, met))

    print()
    print("Reading: branch-and-bound must examine far more of the tree than")
    print("satisfaction search, since it cannot stop at the first valid leaf.")
    print("Value ordering (unserved zones before idle) plus the optimistic")
    print("bound is what keeps this in the tens of nodes rather than the")
    print("200,000-node cap an unordered search hit on the same instance.")


def main():
    table_a()
    table_b()


if __name__ == "__main__":
    main()
