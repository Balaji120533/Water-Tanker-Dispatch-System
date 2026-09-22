"""
Simulates a week of dispatch to make the FAIRNESS claim measurable rather
than asserted (CLAUDE.md Phase 6).

How a day works:
  1. Each zone's tank level determines entitlement via Phase 0's engine.
  2. Entitled zones form the CSP instance; Phase 1's solver allocates.
  3. Zones that received water refill; zones that didn't keep draining --
     so a repeatedly-skipped zone gets progressively more entitled, and
     eventually high-priority. That escalation is exactly what makes the
     fairness question answerable: if the allocator is fair, no zone
     should sit unserved while its level keeps falling.

Pure module (Rule 4): no web/LLM code, returns structured results.
"""

from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase1_csp"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase0_entitlement"))

from problem import Tanker, Zone, build_problem, TANKERS, NUM_SLOTS  # noqa: E402
from constraints import apply_capacity_constraint  # noqa: E402
from ac3 import ac3  # noqa: E402
from solver import solve as csp_solve  # noqa: E402
from soft_constraints import solve_best  # noqa: E402

from logic import Clause, Term  # noqa: E402
from parser import parse_kb  # noqa: E402
from engine import Engine  # noqa: E402

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "phase0_entitlement", "knowledge_base.txt")
_RULES = parse_kb(KB_PATH)

# All 15 GCC zones -- the week runs over the full set, not just the 8 that
# happened to be entitled in Phase 0's sample snapshot.
ALL_ZONES = [
    "thiruvotriyur", "manali", "madhavaram", "tondiarpet", "royapuram",
    "thiruvika_nagar", "ambattur", "anna_nagar", "teynampet", "kodambakkam",
    "valasaravakkam", "alandur", "adyar", "perungudi", "sozhanganallur",
]

# Zones hosting a school/hospital/clinic (from Phase 0's sample facts).
CRITICAL_FACILITY_ZONES = {"tondiarpet", "thiruvika_nagar", "adyar"}

DAILY_DRAIN_PERCENT = 22  # consumption between one day's dispatch and the next
REFILL_TO_PERCENT = 100   # a served zone's tank is topped up

NEED_HIGH_PRIORITY = 10000
NEED_NORMAL = 6000


@dataclass
class DayResult:
    day: int
    entitled: list[str]
    high_priority: list[str]
    served: list[str]
    unserved_entitled: list[str]
    levels_before: dict = field(default_factory=dict)


def classify(levels: dict[str, int], days_since: dict[str, int]) -> tuple[list[str], list[str]]:
    """
    Ask Phase 0's engine which zones are entitled / high priority today.
    The decision is the engine's, not ours -- we only assemble the facts.
    """
    facts = []
    for zone in ALL_ZONES:
        facts.append(Clause(Term("tank_level", (zone, int(levels[zone])))))
        facts.append(Clause(Term("days_since_delivery", (zone, int(days_since[zone])))))
        if zone in CRITICAL_FACILITY_ZONES:
            facts.append(Clause(Term("has_critical_facility", (zone,))))

    engine = Engine(_RULES + facts)
    derived = engine.forward_chain()
    entitled = sorted(f.args[0] for f in derived if f.predicate == "entitled")
    high_priority = sorted(f.args[0] for f in derived if f.predicate == "high_priority")
    return entitled, high_priority


def allocate(entitled: list[str], high_priority: list[str], tankers=None, zone_order=None):
    """
    Run Phase 1's CSP solver for one day. `zone_order` lets a caller
    control which zones the solver reaches first -- that is the hook the
    fairness soft constraint uses, without touching the solver itself.
    """
    if not entitled:
        return {}, []

    names = zone_order if zone_order is not None else entitled
    zones = [
        Zone(
            name,
            NEED_HIGH_PRIORITY if name in high_priority else NEED_NORMAL,
            name in high_priority,
        )
        for name in names
    ]
    problem = build_problem(tankers=tankers or TANKERS, zones=zones, num_slots=NUM_SLOTS)
    apply_capacity_constraint(problem)
    ac3(problem)

    # solve_best (soft constraints) rather than csp_solve: the plain solver
    # returns the FIRST schedule satisfying the hard constraints, and
    # "every tanker idle" qualifies -- which would make any fairness
    # measurement meaningless.
    solution, _, _ = solve_best(problem)
    if solution is None:
        return {}, []

    # A zone counts as served only when its deliveries cover its need.
    supplied: dict[str, int] = {}
    for (tanker_id, _slot), zone_name in solution.items():
        if zone_name is None:
            continue
        supplied[zone_name] = supplied.get(zone_name, 0) + problem.tanker_by_id(tanker_id).capacity_liters

    served = sorted(
        name for name, litres in supplied.items() if litres >= problem.zone_by_name(name).need_liters
    )
    return solution, served


def run_week(
    days: int = 7,
    fairness_soft_constraint: bool = False,
    start_level: int = 55,
    tankers=None,
):
    """
    Run `days` days of dispatch. With fairness_soft_constraint=True, zones
    that have waited longest are offered to the solver first -- a soft
    preference (it never makes an infeasible schedule feasible, and never
    overrides a hard constraint), which is exactly what Unit III means by
    a soft constraint for weekly fairness.
    """
    levels = {z: start_level for z in ALL_ZONES}
    days_since = {z: 0 for z in ALL_ZONES}
    results: list[DayResult] = []

    for day in range(1, days + 1):
        levels_before = dict(levels)
        entitled, high_priority = classify(levels, days_since)

        zone_order = None
        if fairness_soft_constraint and entitled:
            # Longest-waiting first; ties broken by lowest tank level.
            zone_order = sorted(entitled, key=lambda z: (-days_since[z], levels[z]))

        _, served = allocate(entitled, high_priority, tankers=tankers, zone_order=zone_order)

        results.append(
            DayResult(
                day=day,
                entitled=entitled,
                high_priority=high_priority,
                served=served,
                unserved_entitled=[z for z in entitled if z not in served],
                levels_before=levels_before,
            )
        )

        # End of day: served zones refill, everyone else drains further.
        for zone in ALL_ZONES:
            if zone in served:
                levels[zone] = REFILL_TO_PERCENT
                days_since[zone] = 0
            else:
                levels[zone] = max(0, levels[zone] - DAILY_DRAIN_PERCENT)
                days_since[zone] += 1

    return results, levels, days_since


def fairness_report(results: list[DayResult], final_days_since: dict[str, int]) -> dict:
    """Aggregate the week into the numbers that answer 'is this fair?'."""
    times_served = {z: 0 for z in ALL_ZONES}
    times_entitled = {z: 0 for z in ALL_ZONES}
    times_skipped = {z: 0 for z in ALL_ZONES}

    for r in results:
        for z in r.served:
            times_served[z] += 1
        for z in r.entitled:
            times_entitled[z] += 1
        for z in r.unserved_entitled:
            times_skipped[z] += 1

    # Longest run of consecutive days a zone was entitled but not served --
    # the sharpest single measure of "repeatedly skipped".
    longest_skip_streak = {z: 0 for z in ALL_ZONES}
    current = {z: 0 for z in ALL_ZONES}
    for r in results:
        for z in ALL_ZONES:
            if z in r.unserved_entitled:
                current[z] += 1
                longest_skip_streak[z] = max(longest_skip_streak[z], current[z])
            else:
                current[z] = 0

    served_counts = list(times_served.values())
    return {
        "times_served": times_served,
        "times_entitled": times_entitled,
        "times_skipped": times_skipped,
        "longest_skip_streak": longest_skip_streak,
        "max_skip_streak": max(longest_skip_streak.values()),
        "never_served": sorted(z for z, n in times_served.items() if n == 0),
        "min_served": min(served_counts),
        "max_served": max(served_counts),
        "spread": max(served_counts) - min(served_counts),
        "final_days_since": final_days_since,
    }
