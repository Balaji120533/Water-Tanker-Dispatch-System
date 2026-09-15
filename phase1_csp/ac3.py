"""
AC-3 (Arc Consistency Algorithm #3) constraint propagation.

Runs BEFORE search, on domains alone (no partial assignment yet). For every
directed arc (Xi, Xj), it removes any value from Xi's domain that has no
supporting value left in Xj's domain — i.e. a value that could never be
extended into a consistent assignment no matter what search does later.
This shrinks domains up front so backtracking has less to explore.

Pure module: operates only on CSPProblem's domains dict plus the arc list
built from our two binary constraints (refill, no-double-booking).
"""

from __future__ import annotations
from collections import deque
from problem import CSPProblem


def build_arcs(problem: CSPProblem) -> list[tuple[tuple, tuple]]:
    """
    Build the list of directed arcs (Xi, Xj) that AC-3 must check.

    Two families of binary constraint connect our variables:
    1. Refill: (tanker, slot) <-> (tanker, slot+1) for the same tanker
       (consecutive slots).
    2. No-double-booking: (tanker_a, slot) <-> (tanker_b, slot) for every
       pair of distinct tankers in the same slot.
    Each undirected constraint contributes both directions as separate arcs,
    since AC-3 enforces consistency of Xi with respect to Xj specifically.
    """
    arcs = []
    tanker_ids = [t.id for t in problem.tankers]

    # Refill arcs: consecutive slots of the same tanker.
    for tanker_id in tanker_ids:
        for slot in range(problem.num_slots - 1):
            xi = (tanker_id, slot)
            xj = (tanker_id, slot + 1)
            arcs.append((xi, xj))
            arcs.append((xj, xi))

    # No-double-booking arcs: every pair of distinct tankers, same slot.
    for slot in range(problem.num_slots):
        for i, t1 in enumerate(tanker_ids):
            for t2 in tanker_ids[i + 1:]:
                xi = (t1, slot)
                xj = (t2, slot)
                arcs.append((xi, xj))
                arcs.append((xj, xi))

    return arcs


def _consistent_pair(xi: tuple, vi, xj: tuple, vj, is_refill_pair: bool) -> bool:
    """
    True if value vi (for var xi) and value vj (for var xj) can coexist,
    i.e. they do NOT violate the binary constraint connecting xi and xj.
    """
    if is_refill_pair:
        # refill: cannot both be non-idle deliveries in consecutive slots
        if vi is not None and vj is not None:
            return False
        return True
    else:
        # no-double-booking: cannot both deliver to the same zone, same slot
        if vi is not None and vi == vj:
            return False
        return True


def _is_refill_arc(xi: tuple, xj: tuple) -> bool:
    """Same tanker on both sides -> this is a refill arc, not a same-slot arc."""
    return xi[0] == xj[0]


def revise(problem: CSPProblem, xi: tuple, xj: tuple) -> bool:
    """
    Remove values from Xi's domain that have no supporting value in Xj's
    domain. Returns True if Xi's domain was changed.
    """
    revised = False
    is_refill = _is_refill_arc(xi, xj)

    to_remove = []
    for vi in problem.domains[xi]:
        # Does some value vj in Xj's domain satisfy the constraint with vi?
        if not any(
            _consistent_pair(xi, vi, xj, vj, is_refill) for vj in problem.domains[xj]
        ):
            to_remove.append(vi)

    if to_remove:
        problem.domains[xi] = [v for v in problem.domains[xi] if v not in to_remove]
        revised = True

    return revised


def ac3(problem: CSPProblem) -> bool:
    """
    Run AC-3 to a fixpoint. Returns False if any domain is emptied (the
    problem is provably unsatisfiable), True otherwise.

    Standard queue-based algorithm: start with every arc in the queue; each
    time an arc's Xi domain is revised (shrunk), re-add every arc (Xk, Xi)
    for neighbors Xk of Xi, because Xi's shrinking might now make some of
    Xk's values unsupported too.
    """
    arcs = build_arcs(problem)
    queue = deque(arcs)

    # Precompute, for each variable, which arcs point INTO it (its
    # neighbors), so that after revising Xi we know which arcs to re-check.
    neighbors_in: dict[tuple, list[tuple]] = {var: [] for var in problem.variables}
    for xi, xj in arcs:
        neighbors_in[xj].append(xi)

    while queue:
        xi, xj = queue.popleft()
        if revise(problem, xi, xj):
            if not problem.domains[xi]:
                return False  # domain wiped out -> no solution possible
            for xk in neighbors_in[xi]:
                if xk != xj:
                    queue.append((xk, xi))

    return True
