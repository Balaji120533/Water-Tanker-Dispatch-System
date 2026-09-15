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
