"""
Min-conflicts local search for REPAIR (Phase 3, Unit III). Pure module
(Rule 4): no web/LLM code, takes a CSPProblem + a starting (possibly
broken) complete assignment, returns a repaired assignment plus a diff of
what moved and why.

Reuses Phase 1's constraint functions directly rather than re-implementing
them, so repair and initial solving always agree on what "valid" means.
"""

from __future__ import annotations
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase1_csp"))
from problem import CSPProblem  # noqa: E402
from constraints import refill_ok, no_double_booking_ok  # noqa: E402


def count_conflicts(
    problem: CSPProblem, assignment: dict, var: tuple, must_serve: frozenset = frozenset()
) -> int:
    """
    Count how many constraints `var`'s CURRENT value in `assignment`
    violates, against the rest of the (complete) assignment. Unlike the
    backtracking solver's is_consistent (checked against a partial,
    growing assignment), this checks against a full assignment that may
    already be inconsistent -- exactly the situation after a disruption.

    `must_serve`: zone names that a repair scenario requires to appear
    SOMEWHERE in the schedule (e.g. an urgent request). Dropping a
    must-serve zone to idle has zero cost under the hard constraints alone
    -- min-conflicts would happily "repair" by abandoning it -- so this is
    folded in as an extra soft signal: a must-serve zone missing from the
    whole assignment counts as one conflict on every variable currently
    idle (making "stay idle while a must-serve zone goes unserved" no
    longer conflict-free, which is what makes repair actually place it).
    """
    tanker_id, slot = var
    value = assignment[var]
    all_tanker_ids = [t.id for t in problem.tankers]

    conflicts = 0

    # refill_ok as written checks against whatever's already assigned for
    # the neighboring slots; since assignment is complete here, this
    # correctly detects a refill violation either direction.
    if not refill_ok(assignment, tanker_id, slot, value, problem.num_slots):
        conflicts += 1

    if not no_double_booking_ok(assignment, tanker_id, slot, value, all_tanker_ids):
        conflicts += 1

    # capacity is a unary constraint -- check directly against the domain
    # this variable was pruned to (a value outside the pruned domain
    # violates capacity).
    if value is not None and value not in problem.domains[var]:
        conflicts += 1

    if must_serve:
        served = set(assignment.values())
        unserved_must_serve = must_serve - served
        if unserved_must_serve and value is None:
            conflicts += 1

    return conflicts


def total_conflicts(problem: CSPProblem, assignment: dict, must_serve: frozenset = frozenset()) -> int:
    return sum(count_conflicts(problem, assignment, var, must_serve) for var in problem.variables)


def conflicted_variables(problem: CSPProblem, assignment: dict, must_serve: frozenset = frozenset()) -> list[tuple]:
    return [
        var for var in problem.variables if count_conflicts(problem, assignment, var, must_serve) > 0
    ]


def min_conflicts_value(
    problem: CSPProblem,
    assignment: dict,
    var: tuple,
    rng: random.Random,
    must_serve: frozenset = frozenset(),
):
    """
    Among all values in var's domain, return the one(s) that minimize the
    number of conflicts if var were reassigned to it (with everything else
    held fixed) -- ties broken randomly, which is what keeps min-conflicts
    from getting stuck cycling between two equally-bad values.
    """
    best_conflicts = None
    best_candidates = []

    for value in problem.domains[var]:
        trial = dict(assignment)
        trial[var] = value
        conflicts = count_conflicts(problem, trial, var, must_serve)
        # also need to count conflicts THIS reassignment causes for
        # neighbors, not just for var itself -- use total over var's
        # relevant neighborhood by checking total_conflicts delta cheaply
        # via a full recount restricted to var and its potential partners.
        neighbor_conflicts = _neighborhood_conflicts(problem, trial, var, must_serve)
        score = conflicts + neighbor_conflicts

        if best_conflicts is None or score < best_conflicts:
            best_conflicts = score
            best_candidates = [value]
        elif score == best_conflicts:
            best_candidates.append(value)

    return rng.choice(best_candidates)


def _neighborhood_conflicts(
    problem: CSPProblem, assignment: dict, var: tuple, must_serve: frozenset = frozenset()
) -> int:
    """Sum of conflicts over every OTHER variable that shares a constraint with var."""
    tanker_id, slot = var
    neighbors = []
    for neighbor_slot in (slot - 1, slot + 1):
        if 0 <= neighbor_slot < problem.num_slots:
            neighbors.append((tanker_id, neighbor_slot))
    for t in problem.tankers:
        if t.id != tanker_id:
            neighbors.append((t.id, slot))
    return sum(count_conflicts(problem, assignment, n, must_serve) for n in neighbors)


def repair(
    problem: CSPProblem,
    broken_assignment: dict,
    max_steps: int = 1000,
    seed: int | None = None,
    must_serve: frozenset = frozenset(),
) -> tuple[dict | None, list[dict], int]:
    """
    Min-conflicts repair. Starting from `broken_assignment` (a complete
    assignment that may violate constraints after a disruption), repeatedly
    pick a randomly-chosen conflicted variable and reassign it to the value
    that minimizes conflicts, until no conflicts remain or max_steps is hit.

    `must_serve`: zone names (e.g. an urgent request) that must appear
    SOMEWHERE in the final assignment, not just be conflict-free -- passed
    through to count_conflicts as an extra soft signal so repair doesn't
    "fix" an urgent-request disruption by simply dropping the urgent zone
    back to idle (which would otherwise be conflict-free and cost nothing).

    Returns (repaired_assignment_or_None, diff, steps_taken). diff is a
    list of {"variable", "from", "to"} dicts describing every change made,
    in order -- the "smallest change" output CLAUDE.md requires, not a
    fresh schedule.
    """
    rng = random.Random(seed)
    assignment = dict(broken_assignment)
    diff = []

    for step in range(max_steps):
        conflicted = conflicted_variables(problem, assignment, must_serve)
        if not conflicted:
            return assignment, diff, step

        var = rng.choice(conflicted)
        old_value = assignment[var]
        new_value = min_conflicts_value(problem, assignment, var, rng, must_serve)

        if new_value != old_value:
            assignment[var] = new_value
            diff.append({"variable": var, "from": old_value, "to": new_value})

    # Ran out of steps -- return whatever we have plus whether it's fully repaired.
    if not conflicted_variables(problem, assignment, must_serve):
        return assignment, diff, max_steps
    return None, diff, max_steps
