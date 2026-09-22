"""
Soft constraints (Unit III): preferences that shape WHICH valid schedule
is chosen, without ever making a schedule infeasible.

The hard constraints in constraints.py say what is *allowed*. They do not
say what is *good* -- and "every tanker idle" is allowed, which is why the
plain solver could return a schedule leaving entitled zones unserved while
tankers sat unused.

This module adds the missing objective: among all schedules satisfying the
hard constraints, prefer the one that serves the most entitled zones, with
high-priority zones weighted more heavily. Crucially, if demand genuinely
exceeds fleet capacity, this still returns the best PARTIAL schedule --
where a hard "must serve everyone" constraint would return nothing at all.

Pure module (Rule 4): structured input, structured output.
"""

from __future__ import annotations
from problem import CSPProblem
from solver import is_consistent, SolveStats
from heuristics import select_var_mrv_degree, order_values_lcv

HIGH_PRIORITY_WEIGHT = 10
NORMAL_WEIGHT = 1


def schedule_score(problem: CSPProblem, assignment: dict) -> int:
    """
    Soft-constraint objective: how good is this schedule?

    A zone scores only when its need is actually MET -- a zone needing
    10,000L that received a single 9,000L tanker is still short, and
    scoring it as "served" would let the solver claim credit for a
    delivery that left residents without water. High-priority zones are
    worth more, so when the fleet cannot cover everyone the solver
    sacrifices a normal zone before a high-priority one.
    """
    supplied: dict[str, int] = {}
    for (tanker_id, _slot), zone_name in assignment.items():
        if zone_name is None:
            continue
        supplied[zone_name] = supplied.get(zone_name, 0) + problem.tanker_by_id(tanker_id).capacity_liters

    score = 0
    for zone_name, litres in supplied.items():
        zone = problem.zone_by_name(zone_name)
        if litres >= zone.need_liters:
            score += HIGH_PRIORITY_WEIGHT if zone.is_high_priority else NORMAL_WEIGHT
    return score


def solve_best(problem: CSPProblem, max_nodes: int = 200_000) -> tuple[dict | None, SolveStats, int]:
    """
    Branch-and-bound over the same search tree the plain solver walks, but
    instead of returning the first valid schedule it keeps searching and
    returns the highest-scoring one.

    Two things make this tractable at our sizes:

    1. Value ordering tries UNSERVED zones before already-served ones, and
       idle last. Plain LCV ordering happily tries idle first, which wastes
       the entire budget exploring schedules that leave tankers unused.
    2. An optimistic bound prunes any branch that could not beat the best
       score found so far, even if every remaining zone were served.

    Returns (best_assignment, stats, best_score).
    """
    stats = SolveStats()
    best: dict = {}
    best_score = -1

    zone_weight = {
        z.name: (HIGH_PRIORITY_WEIGHT if z.is_high_priority else NORMAL_WEIGHT)
        for z in problem.zones
    }
    total_possible = sum(zone_weight.values())

    # Fixed variable order: slot-major, so each tanker's day fills in
    # sequence. Cheaper than recomputing MRV at every node, and with the
    # value ordering below it reaches good schedules almost immediately.
    ordered_vars = sorted(problem.variables, key=lambda v: (v[1], v[0]))

    need = {z.name: z.need_liters for z in problem.zones}

    def backtrack(assignment: dict, supplied: dict, score: int, index: int):
        nonlocal best, best_score

        if stats.nodes_explored >= max_nodes:
            return
        stats.nodes_explored += 1

        if index == len(ordered_vars):
            if score > best_score:
                best_score = score
                best = dict(assignment)
            return

        # Optimistic bound: assume every not-yet-satisfied zone still could
        # be satisfied. If even that cannot beat `best`, abandon the branch.
        upper = score + sum(w for z, w in zone_weight.items() if supplied.get(z, 0) < need[z])
        if upper <= best_score:
            return

        var = ordered_vars[index]

        # Zones still short of their need first (heaviest first), then idle.
        # Trying idle last is what stops the search settling for empty
        # schedules; keeping short zones as candidates is what lets a
        # 10,000L zone receive the second delivery it needs.
        candidates = [
            v for v in problem.domains[var]
            if v is not None and supplied.get(v, 0) < need[v]
        ]
        candidates.sort(key=lambda z: -zone_weight[z])
        candidates.append(None)

        for value in candidates:
            if not is_consistent(problem, assignment, var, value):
                continue
            assignment[var] = value
            if value is None:
                backtrack(assignment, supplied, score, index + 1)
            else:
                before = supplied.get(value, 0)
                after = before + problem.tanker_by_id(var[0]).capacity_liters
                supplied[value] = after
                # A zone scores at the moment its need is first met.
                gained = zone_weight[value] if (before < need[value] <= after) else 0
                backtrack(assignment, supplied, score + gained, index + 1)
                if before:
                    supplied[value] = before
                else:
                    del supplied[value]
            del assignment[var]

    backtrack({}, {}, 0, 0)
    return (best or None), stats, best_score
