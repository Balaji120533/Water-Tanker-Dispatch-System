"""
Small adapter into Phase 0's entitlement engine for a single ad-hoc
tank_level fact (used by the partial-observability simulator and the
volunteer NL-parsing flow). Does not decide anything itself -- it only
constructs a fact and asks Phase 0's real backward chaining to decide,
exactly like the FastAPI backend's /api/volunteer/report endpoint does.
"""

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase0_entitlement"))

from logic import Clause, Term  # noqa: E402
from parser import parse_kb  # noqa: E402
from engine import Engine  # noqa: E402

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "phase0_entitlement", "knowledge_base.txt")
_RULES = parse_kb(KB_PATH)


def decide(zone_name: str, tank_level_percent: float, days_since_delivery: int = 0) -> str:
    """
    Returns one of "high_priority", "entitled", "not_entitled" -- the
    entitlement engine's actual decision for this single fact, nothing
    invented here.
    """
    facts = [
        Clause(Term("tank_level", (zone_name, int(tank_level_percent)))),
        Clause(Term("days_since_delivery", (zone_name, days_since_delivery))),
    ]
    engine = Engine(_RULES + facts)

    if engine.backward_chain(Term("high_priority", (zone_name,))):
        return "high_priority"
    if engine.backward_chain(Term("entitled", (zone_name,))):
        return "entitled"
    return "not_entitled"
