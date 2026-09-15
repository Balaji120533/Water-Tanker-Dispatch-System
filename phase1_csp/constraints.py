"""
Hard constraints for the tanker -> zone CSP, added ONE AT A TIME (Rule 3).

Each constraint function takes a CSPProblem and either prunes domains
in-place (for unary constraints) or is checked during search (for
constraints that involve more than one variable). Every constraint added
here must have a corresponding test in tests/ proving it holds before the
next constraint is added.
"""

from __future__ import annotations
from problem import CSPProblem


def apply_capacity_constraint(problem: CSPProblem) -> None:
    """
    Constraint (a): a tanker can only be assigned to a zone if its capacity
    is enough to cover that zone's water need.

    This is a UNARY constraint (it only involves one variable's value at a
    time — the zone assigned to a single (tanker, slot) pair), so instead of
    checking it during search we prune it directly out of each variable's
    domain up front. None (idle) always stays a valid domain value: idling
    trivially cannot violate a capacity constraint.
    """
    for (tanker_id, slot), domain in problem.domains.items():
        tanker = problem.tanker_by_id(tanker_id)
        problem.domains[(tanker_id, slot)] = [
            zone_name
            for zone_name in domain
            if zone_name is None or problem.zone_by_name(zone_name).need_liters <= tanker.capacity_liters
        ]


def refill_ok(assignment: dict, tanker_id: str, slot: int, value, num_slots: int) -> bool:
    """
    Constraint (b): refill at a source station between deliveries.

    Modeled as — a tanker that delivered (was assigned a non-None zone) in
    slot N must be idle (None) in slot N+1; that idle slot stands in for the
    refill/travel trip. Real station coordinates and travel time arrive in
    Phase 2 routing — this phase only needs the scheduling shape of the
    constraint, not the geography.

    This is a BINARY constraint between (tanker_id, slot-1)/(tanker_id, slot)
    and (tanker_id, slot)/(tanker_id, slot+1), so unlike capacity it cannot
    be pruned out of a single variable's domain in advance — it depends on
    what value the *other* variable takes, which is only known during
    search. Called from the backtracking search's consistency check.
    """
    # Check against the slot immediately before this one.
    prev_key = (tanker_id, slot - 1)
    if slot - 1 >= 0 and prev_key in assignment:
        prev_value = assignment[prev_key]
        if prev_value is not None and value is not None:
            return False  # previous slot delivered -> this slot must be idle

    # Check against the slot immediately after this one, if already assigned
    # (can happen when the solver assigns slots out of increasing order).
    next_key = (tanker_id, slot + 1)
    if slot + 1 < num_slots and next_key in assignment:
        next_value = assignment[next_key]
        if value is not None and next_value is not None:
            return False  # this slot delivered -> next slot must be idle

    return True
