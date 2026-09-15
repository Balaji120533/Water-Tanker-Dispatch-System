"""
Variable- and value-ordering heuristics for backtracking search.

MRV (Minimum Remaining Values) and degree pick WHICH unassigned variable
to branch on next. LCV (Least Constraining Value) picks WHICH value to try
first for the chosen variable. None of these change what counts as a
solution — they only change the order the same search tree is explored in,
which is why they can be benchmarked directly against plain backtracking.
"""

from __future__ import annotations
from problem import CSPProblem
from constraints import refill_ok, no_double_booking_ok


def count_remaining_values(problem: CSPProblem, assignment: dict, var: tuple) -> int:
    """How many values in var's domain are still consistent with the partial assignment."""
    tanker_id, slot = var
    all_tanker_ids = [t.id for t in problem.tankers]
    count = 0
    for value in problem.domains[var]:
        if refill_ok(assignment, tanker_id, slot, value, problem.num_slots) and \
           no_double_booking_ok(assignment, tanker_id, slot, value, all_tanker_ids):
            count += 1
    return count


def degree(problem: CSPProblem, assignment: dict, var: tuple) -> int:
    """
    Number of constraints var has with OTHER still-unassigned variables.
    Higher degree = more future variables this choice could constrain, so
    picking it early prunes the remaining search tree faster.
    """
    tanker_id, slot = var
    count = 0
    # refill neighbors
    for neighbor_slot in (slot - 1, slot + 1):
        if 0 <= neighbor_slot < problem.num_slots:
            neighbor = (tanker_id, neighbor_slot)
            if neighbor not in assignment:
                count += 1
    # same-slot, other-tanker neighbors
    for t in problem.tankers:
        if t.id != tanker_id:
            neighbor = (t.id, slot)
            if neighbor not in assignment:
                count += 1
    return count


def select_var_mrv(problem: CSPProblem, assignment: dict):
    """
    MRV: pick the unassigned variable with the FEWEST legal values left.
    Intuition: that variable is most likely to fail, so trying it first
    fails fast instead of wasting work on easier variables first.
    """
    unassigned = [v for v in problem.variables if v not in assignment]
    if not unassigned:
        return None
    return min(unassigned, key=lambda v: count_remaining_values(problem, assignment, v))


def select_var_mrv_degree(problem: CSPProblem, assignment: dict):
    """
    MRV, with DEGREE as the tie-breaker. When two variables are equally
    constrained by remaining-values, prefer the one that constrains more
    OTHER unassigned variables (higher degree), since resolving it prunes
    more of the remaining tree.
    """
    unassigned = [v for v in problem.variables if v not in assignment]
    if not unassigned:
        return None
    return min(
        unassigned,
        key=lambda v: (
            count_remaining_values(problem, assignment, v),
            -degree(problem, assignment, v),
        ),
    )


def order_values_lcv(problem: CSPProblem, assignment: dict, var: tuple):
    """
    LCV: try values that rule out the FEWEST choices for neighboring
    variables first. Intuition: unlike MRV/degree (which pick the variable
    likely to fail fast), LCV is applied to VALUES and does the opposite —
    it keeps options open for the rest of the search, reducing the chance
    of a dead end later.
    """
    tanker_id, slot = var
    all_tanker_ids = [t.id for t in problem.tankers]

    def values_ruled_out(value):
        if value is None:
            return 0  # idle never constrains any neighbor
        ruled_out = 0
        # neighbors via refill: same tanker, adjacent slot
        for neighbor_slot in (slot - 1, slot + 1):
            if 0 <= neighbor_slot < problem.num_slots:
                neighbor = (tanker_id, neighbor_slot)
                if neighbor not in assignment:
                    # a non-idle value here forces idle there, so every
                    # non-idle option previously open for that neighbor
                    # is ruled out.
                    ruled_out += sum(1 for v in problem.domains[neighbor] if v is not None)
        # neighbors via same-slot double-booking
        for t in problem.tankers:
            if t.id != tanker_id:
                neighbor = (t.id, slot)
                if neighbor not in assignment and value in problem.domains[neighbor]:
                    ruled_out += 1
        return ruled_out

    return sorted(problem.domains[var], key=values_ruled_out)
