"""
CSP problem representation for tanker -> zone allocation.

Pure module: no web code, no LLM calls, no I/O beyond loading its own static
input data. Takes structured input, returns structured output (Rule 4).

Variables: (tanker_id, time_slot) pairs, e.g. ("T1", 0).
Domain of each variable: the set of zone names it could be assigned to, plus
the special value None meaning "idle this slot" (a tanker need not deliver
in every slot).
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tanker:
    id: str
    capacity_liters: int


@dataclass(frozen=True)
class Zone:
    name: str
    need_liters: int
    is_high_priority: bool


# --- Confirmed fleet (Phase 1 ASK-ME answer) --------------------------------
TANKERS: list[Tanker] = [
    Tanker("T1", 9000),
    Tanker("T2", 9000),
    Tanker("T3", 9000),
    Tanker("T4", 12000),
    Tanker("T5", 12000),
]

# --- Entitled zones, from Phase 0's forward-chaining output ----------------
# high_priority -> 10000L need, normal entitled -> 6000L need (ASK-ME answer)
ZONES: list[Zone] = [
    Zone("teynampet", 10000, True),
    Zone("tondiarpet", 10000, True),
    Zone("thiruvotriyur", 6000, False),
    Zone("manali", 6000, False),
    Zone("royapuram", 6000, False),
    Zone("kodambakkam", 6000, False),
    Zone("alandur", 6000, False),
    Zone("perungudi", 6000, False),
]

NUM_SLOTS = 3  # time-slots in a working day, small on purpose (Rule 5)


@dataclass
class CSPProblem:
    """
    Structured CSP input: variables, domains, and constraint data. Built by
    build_problem(); consumed by the solver in solver.py.
    """
    tankers: list[Tanker]
    zones: list[Zone]
    num_slots: int
    variables: list[tuple[str, int]] = field(default_factory=list)
    domains: dict = field(default_factory=dict)  # var -> list of zone names (or None)

    def zone_by_name(self, name: str) -> Zone:
        return next(z for z in self.zones if z.name == name)

    def tanker_by_id(self, tid: str) -> Tanker:
        return next(t for t in self.tankers if t.id == tid)


def build_problem(
    tankers: list[Tanker] = None,
    zones: list[Zone] = None,
    num_slots: int = NUM_SLOTS,
) -> CSPProblem:
    tankers = tankers if tankers is not None else TANKERS
    zones = zones if zones is not None else ZONES

    variables = [(t.id, slot) for t in tankers for slot in range(num_slots)]
    zone_names = [z.name for z in zones]
    # Initial domain before constraint filtering: any zone, or idle (None).
    domains = {var: list(zone_names) + [None] for var in variables}

    return CSPProblem(
        tankers=tankers,
        zones=zones,
        num_slots=num_slots,
        variables=variables,
        domains=domains,
    )
