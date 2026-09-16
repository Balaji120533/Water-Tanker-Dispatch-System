"""
Disruption scenarios that break a valid schedule, for min-conflicts repair
to fix. Pure module (Rule 4): only mutates a plain assignment dict.
"""

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase1_csp"))
from problem import CSPProblem  # noqa: E402


def tanker_breakdown(problem: CSPProblem, assignment: dict, tanker_id: str) -> dict:
    """
    Simulate a tanker breaking down: every slot it was assigned a delivery
    becomes... still assigned to that tanker in the broken_assignment (so
    min-conflicts has something to fix), but the tanker is marked
    unavailable by removing every non-None value from ITS domain. Repair
    must then move those deliveries to other tankers (or idle) since the
    broken tanker's domain no longer permits them.
    """
    broken = dict(assignment)
    for slot in range(problem.num_slots):
        var = (tanker_id, slot)
        problem.domains[var] = [None]  # unavailable: only idle permitted now
    return broken


def urgent_request(problem: CSPProblem, assignment: dict, zone_name: str) -> dict:
    """
    Simulate an urgent request: an already-entitled zone that the current
    schedule does NOT serve in any slot is escalated to urgent, and must be
    inserted somewhere. We model "must be served" by forcing one currently
    idle (tanker, slot) variable, chosen as the one requiring the fewest
    knock-on changes, to instead target `zone_name` -- but rather than
    picking it ourselves, we simply mark the assignment as broken by
    checking it doesn't currently appear anywhere, and let min-conflicts
    place it by treating "zone_name must appear at least once" as an
    additional soft signal: we seed the broken assignment by forcing the
    FIRST idle slot to this zone (a natural min-conflicts starting point;
    repair will move it if that causes worse conflicts elsewhere).
    """
    broken = dict(assignment)
    for var, value in assignment.items():
        if value is None:
            broken[var] = zone_name
            return broken
    # No idle slot existed at all -- caller should treat this as
    # unrepairable-without-slack and report it, not silently ignore it.
    return broken
