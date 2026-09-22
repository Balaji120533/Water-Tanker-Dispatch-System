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
    Constraint (a): a tanker may only be sent to a zone it can usefully
    supply -- i.e. it must carry a non-zero load.

    NOTE on the relaxation: this originally pruned any zone whose need
    exceeded a single tanker's capacity, which made a 10,000L zone
    invisible to every 9,000L tanker. That directly contradicted
    constraint (d), which exists precisely so several deliveries can
    accumulate to cover a large zone -- the result was that a zone bigger
    than the largest FREE tanker became silently unservable even when two
    trips would have covered it comfortably.

    A zone's need is met by the SUM of its deliveries, so capacity is
    enforced by (d) (never oversupply) rather than by pruning here. Every
    tanker can carry water to every zone; what differs is how many trips
    are needed.

    Kept as a domain-pruning pass (rather than deleted) because it remains
    the right place for genuinely unary restrictions, and the benchmark
    tables reference this stage.
    """
    for (tanker_id, slot), domain in problem.domains.items():
        tanker = problem.tanker_by_id(tanker_id)
        problem.domains[(tanker_id, slot)] = [
            zone_name
            for zone_name in domain
            if zone_name is None or tanker.capacity_liters > 0
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


def zone_not_oversupplied_ok(problem, assignment: dict, tanker_id: str, slot: int, value) -> bool:
    """
    Constraint (d): a zone receives no more water than it actually needs.

    Without this, nothing stopped the solver parking ONE zone in every
    available slot while other entitled zones got nothing -- the schedule
    was "valid" under (a)-(c) but useless, and made the fairness claim
    impossible to satisfy.

    A zone may legitimately need more than one delivery: a 10,000L zone
    cannot be covered by a single 9,000L tanker, so forbidding a second
    visit outright would make it permanently unservable. The rule is
    therefore about VOLUME, not visit count -- deliveries to a zone may
    continue until its need is met, and then must stop.

    Concretely: the assigned tankers' capacities, summed over the zone's
    deliveries, may not exceed its need by a full extra delivery. We allow
    the last delivery to overshoot (you cannot part-fill a tanker run), but
    once need is already covered, another delivery is pure waste.
    """
    if value is None:
        return True  # idle supplies nothing

    zone = problem.zone_by_name(value)
    tanker = problem.tanker_by_id(tanker_id)

    supplied = 0
    for (other_tanker, other_slot), other_value in assignment.items():
        if (other_tanker, other_slot) == (tanker_id, slot):
            continue
        if other_value == value:
            supplied += problem.tanker_by_id(other_tanker).capacity_liters

    # If existing deliveries already cover the need, this one is surplus.
    if supplied >= zone.need_liters:
        return False

    return True


def no_double_booking_ok(assignment: dict, tanker_id: str, slot: int, value, all_tanker_ids: list) -> bool:
    """
    Constraint (c): no tanker double-booked in a slot.

    Variables are already (tanker_id, slot) pairs, so a single tanker
    structurally cannot hold two zone values in the same slot — that
    collision is impossible in this representation. The real resource
    collision left to prevent is the other direction: two DIFFERENT
    tankers both dispatched to the SAME zone in the SAME slot, which would
    double-deliver one zone while other entitled zones go unserved that
    slot. This is a BINARY constraint across tankers sharing a slot,
    checked the same way as refill_ok: against whatever is already in the
    partial assignment.
    """
    if value is None:
        return True  # idle never conflicts with anything

    for other_id in all_tanker_ids:
        if other_id == tanker_id:
            continue
        other_key = (other_id, slot)
        if other_key in assignment and assignment[other_key] == value:
            return False

    return True
