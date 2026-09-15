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
from constraints import refill_ok, no_double_booking_ok
from heuristics import select_var_mrv, select_var_mrv_degree, order_values_lcv


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
    all_tanker_ids = [t.id for t in problem.tankers]
    if not no_double_booking_ok(assignment, tanker_id, slot, value, all_tanker_ids):
        return False
    return True


def select_unassigned_variable_plain(problem: CSPProblem, assignment: dict):
    """Plain ordering: first variable (in declaration order) not yet assigned."""
    for var in problem.variables:
        if var not in assignment:
            return var
    return None


def order_domain_values_plain(problem: CSPProblem, assignment: dict, var: tuple):
    """Plain ordering: domain values in the order they were pruned to."""
    return list(problem.domains[var])


# Heuristic configuration: which variable-selection and value-ordering
# function to use. Selected by name so benchmark.py can loop over
# combinations without duplicating the backtracking loop itself.
VAR_SELECTORS = {
    "none": select_unassigned_variable_plain,
    "mrv": lambda problem, assignment: select_var_mrv(problem, assignment),
    "mrv+degree": lambda problem, assignment: select_var_mrv_degree(problem, assignment),
}

VALUE_ORDERERS = {
    "none": order_domain_values_plain,
    "lcv": lambda problem, assignment, var: order_values_lcv(problem, assignment, var),
}


def backtrack(problem: CSPProblem, assignment: dict, stats: SolveStats, var_selector, value_orderer):
    stats.nodes_explored += 1

    var = var_selector(problem, assignment)
    if var is None:
        return dict(assignment)  # every variable assigned -> solution

    for value in value_orderer(problem, assignment, var):
        if is_consistent(problem, assignment, var, value):
            assignment[var] = value
            result = backtrack(problem, assignment, stats, var_selector, value_orderer)
            if result is not None:
                return result
            del assignment[var]

    return None  # no value worked -> backtrack


def solve(
    problem: CSPProblem, var_heuristic: str = "none", value_heuristic: str = "none"
) -> tuple[dict | None, SolveStats]:
    """
    var_heuristic: "none" | "mrv" | "mrv+degree"
    value_heuristic: "none" | "lcv"
    """
    stats = SolveStats()
    var_selector = VAR_SELECTORS[var_heuristic]
    value_orderer = VALUE_ORDERERS[value_heuristic]
    result = backtrack(problem, {}, stats, var_selector, value_orderer)
    return result, stats
