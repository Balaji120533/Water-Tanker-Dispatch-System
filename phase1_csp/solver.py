"""
Backtracking search for the tanker -> zone CSP. Pure module (Rule 4): takes
a CSPProblem, returns an assignment dict. No web/LLM code in here.

This starts as PLAIN backtracking (no variable/value ordering heuristics).
MRV, degree, and LCV are added later, once all three hard constraints are
in place, so the benchmark log has a true "before heuristics" baseline to
compare against.
"""

from __future__ import annotations
from problem import CSPProblem
from constraints import refill_ok


class SolveStats:
    def __init__(self):
        self.nodes_explored = 0


def is_consistent(problem: CSPProblem, assignment: dict, var: tuple, value) -> bool:
    """
    Check all constraints that involve `var` against the values already in
    `assignment`, as if `var` were also assigned `value`.
    """
    tanker_id, slot = var
    if not refill_ok(assignment, tanker_id, slot, value, problem.num_slots):
        return False
    return True


def select_unassigned_variable(problem: CSPProblem, assignment: dict):
    """Plain ordering: first variable (in declaration order) not yet assigned."""
    for var in problem.variables:
        if var not in assignment:
            return var
    return None


def order_domain_values(problem: CSPProblem, var: tuple):
    """Plain ordering: domain values in the order they were pruned to."""
    return list(problem.domains[var])


def backtrack(problem: CSPProblem, assignment: dict, stats: SolveStats):
    stats.nodes_explored += 1

    var = select_unassigned_variable(problem, assignment)
    if var is None:
        return dict(assignment)  # every variable assigned -> solution

    for value in order_domain_values(problem, var):
        if is_consistent(problem, assignment, var, value):
            assignment[var] = value
            result = backtrack(problem, assignment, stats)
            if result is not None:
                return result
            del assignment[var]

    return None  # no value worked -> backtrack


def solve(problem: CSPProblem) -> tuple[dict | None, SolveStats]:
    stats = SolveStats()
    result = backtrack(problem, {}, stats)
    return result, stats
