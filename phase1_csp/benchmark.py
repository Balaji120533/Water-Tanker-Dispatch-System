"""
Benchmark log: nodes explored and solve time, before vs after each
heuristic (CLAUDE.md Phase 1 deliverable).

Run: python benchmark.py
"""

from __future__ import annotations
import time
import random
from problem import build_problem, Tanker, Zone
from constraints import apply_capacity_constraint
from ac3 import ac3
from solver import solve

RUNS_PER_CONFIG = 200  # small instance -> repeat to get a stable timing signal

CONFIGS = [
    ("no AC-3, plain backtracking", False, "none", "none"),
    ("AC-3, plain backtracking", True, "none", "none"),
    ("AC-3 + MRV", True, "mrv", "none"),
    ("AC-3 + MRV + degree", True, "mrv+degree", "none"),
    ("AC-3 + MRV + degree + LCV", True, "mrv+degree", "lcv"),
]


def run_config(problem_factory, use_ac3: bool, var_h: str, val_h: str):
    problem = problem_factory()
    apply_capacity_constraint(problem)
    if use_ac3:
        ac3(problem)

    start = time.perf_counter()
    solution, stats = solve(problem, var_heuristic=var_h, value_heuristic=val_h)
    elapsed = time.perf_counter() - start

    return solution is not None, stats.nodes_explored, elapsed


def build_stress_problem():
    """
    SYNTHETIC STRESS INSTANCE — NOT real system data.

    The real Phase 1 problem (5 tankers, 8 entitled zones, 3 slots) is
    small enough that plain backtracking already solves it in ~16 nodes,
    which is too easy to show heuristics paying off. Two things make this
    instance actually exercise MRV/degree/LCV instead of tying with plain
    backtracking:

    1. It is TIGHT (zones close to the max deliverable count) so a wrong
       early choice can dead-end instead of always having idle to fall
       back on.
    2. Fleet order is adversarial to plain backtracking's declaration-order
       variable selection: the FIRST tankers declared are the LARGE
       (12000L) ones that fit almost every zone (so plain backtracking
       "wastes" easy, unconstrained choices first), while the LAST
       declared are small 9000L tankers competing over a handful of zones
       that actually fit them (the real bottleneck). Plain order reaches
       the hard variables last, after committing to a large search
       subtree; MRV finds and resolves the tight variables FIRST, which is
       precisely the "fail fast" argument for MRV.
    """
    rng = random.Random(7)

    num_slots = 3
    big_tankers = [Tanker(f"BigT{i}", 12000) for i in range(1, 5)]      # 4 roomy tankers, declared first
    small_tankers = [Tanker(f"SmallT{i}", 9000) for i in range(1, 5)]   # 4 tight tankers, declared last
    tankers = big_tankers + small_tankers

    # Zones sized so ~half need >9000L (only the big tankers can take
    # them) and the rest sit right at 9000L (fit everything) -- and there
    # are enough of them relative to slots that competition is real.
    zones = []
    for i in range(10):
        need = rng.choice([9000, 9000, 11000, 11500])
        zones.append(Zone(f"stress_zone_{i}", need, rng.random() < 0.4))

    return build_problem(tankers=tankers, zones=zones, num_slots=num_slots)


def run_table(label_prefix: str, problem_factory, runs_per_config: int):
    print(f"\n{label_prefix}")
    print(f"{'Configuration':<32} {'Solved':<8} {'Nodes':<8} {'Time (ms)':<12}")
    print("-" * 62)

    for label, use_ac3, var_h, val_h in CONFIGS:
        # First run to get node count (deterministic given fixed problem/heuristics).
        solved, nodes, _ = run_config(problem_factory, use_ac3, var_h, val_h)

        # Repeat for a stabler timing average.
        total_time = 0.0
        for _ in range(runs_per_config):
            _, _, elapsed = run_config(problem_factory, use_ac3, var_h, val_h)
            total_time += elapsed
        avg_ms = (total_time / runs_per_config) * 1000

        print(f"{label:<32} {str(solved):<8} {nodes:<8} {avg_ms:<12.4f}")


def main():
    run_table("REAL PROBLEM (5 tankers, 8 entitled zones, 3 slots)", build_problem, RUNS_PER_CONFIG)
    run_table(
        "SYNTHETIC STRESS INSTANCE (4 big + 4 small tankers, 10 zones, adversarial "
        "declaration order) -- NOT real data, benchmark only",
        build_stress_problem,
        20,  # fewer repeats: this instance is slower per solve
    )


if __name__ == "__main__":
    main()
