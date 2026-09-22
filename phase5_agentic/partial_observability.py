"""
Partial-observability simulator: tank levels drift over time in the real
world, but the dispatch system only ever sees the LAST REPORTED value for
each zone -- it cannot see the true, current level directly. This is the
textbook partially-observable environment: the agent (dispatch system)
acts on a BELIEF STATE built from stale sensor readings, not ground truth.

The system plans on its belief and REPLANS (online search) whenever a new
report arrives and corrects that belief. This file shows the gap between
belief and reality, and demonstrates a mid-day correction.
"""

from __future__ import annotations
from dataclasses import dataclass, field

DRAIN_RATE_PERCENT_PER_HOUR = 5.0  # confirmed: fixed drain rate for this demo


@dataclass
class TrueZoneState:
    """
    Ground truth for one zone -- the ACTUAL water level, which the dispatch
    system never gets to read directly. Only exists inside the simulator to
    show what "reality" was doing while the system's belief was stale.
    """
    zone_name: str
    level_percent: float

    def drain(self, hours: float) -> None:
        self.level_percent = max(0.0, self.level_percent - DRAIN_RATE_PERCENT_PER_HOUR * hours)


@dataclass
class Belief:
    """
    What the dispatch system BELIEVES about a zone: the level as of the
    last report it received, and when that report was made. This is the
    only thing entitlement decisions are ever computed from -- never
    TrueZoneState directly. That separation IS partial observability.
    """
    zone_name: str
    reported_level_percent: float
    reported_at_hour: float

    def staleness_hours(self, current_hour: float) -> float:
        return current_hour - self.reported_at_hour


@dataclass
class SimulationLog:
    events: list = field(default_factory=list)

    def record(self, hour: float, kind: str, detail: str) -> None:
        self.events.append({"hour": hour, "kind": kind, "detail": detail})

    def pretty(self) -> str:
        return "\n".join(f"[t={e['hour']:>5.1f}h] {e['kind']}: {e['detail']}" for e in self.events)


class PartialObservabilitySimulator:
    """
    Drives one zone through a day: the true level drains continuously: the
    system's belief only updates when a report arrives, and each report
    triggers a replan (recompute entitlement from the NEW belief, compare
    against what the OLD belief would have concluded).
    """

    def __init__(self, zone_name: str, initial_level_percent: float):
        self.true_state = TrueZoneState(zone_name, initial_level_percent)
        self.belief = Belief(zone_name, initial_level_percent, reported_at_hour=0.0)
        self.current_hour = 0.0
        self.log = SimulationLog()
        self.log.record(0.0, "initial_report", f"{zone_name} reported at {initial_level_percent}%")

    def advance_to(self, hour: float) -> None:
        """Move simulated time forward; the TRUE level drains, belief does NOT change."""
        if hour < self.current_hour:
            raise ValueError("cannot move simulated time backward")
        elapsed = hour - self.current_hour
        self.true_state.drain(elapsed)
        self.current_hour = hour

    def new_report_arrives(self, reported_level_percent: float) -> dict:
        """
        A fresh report lands: update the belief and RECOMPUTE entitlement
        from it -- this is the "replan" step of online search. Returns a
        dict comparing what the stale belief would have said vs. what the
        corrected belief says, so the correction is visible.
        """
        from engine_bridge import decide  # local import: avoids a hard
        # dependency on phase0 for callers that only want drift mechanics

        old_belief_level = self.belief.reported_level_percent
        old_belief_decision = decide(self.belief.zone_name, old_belief_level)
        staleness = self.belief.staleness_hours(self.current_hour)

        self.belief = Belief(self.true_state.zone_name, reported_level_percent, self.current_hour)
        new_decision = decide(self.belief.zone_name, reported_level_percent)

        self.log.record(
            self.current_hour,
            "new_report",
            f"{self.true_state.zone_name}: reported {reported_level_percent}% "
            f"(previous belief was {staleness:.1f}h stale)",
        )

        changed = old_belief_decision != new_decision
        if changed:
            self.log.record(
                self.current_hour,
                "replan",
                f"belief correction changes decision: {old_belief_decision} -> {new_decision}",
            )

        return {
            "hour": self.current_hour,
            "staleness_hours": staleness,
            "old_belief_level": old_belief_level,
            "old_decision": old_belief_decision,
            "new_decision": new_decision,
            "decision_changed": changed,
            "true_level_at_this_moment": self.true_state.level_percent,
        }

    def belief_vs_reality_gap(self) -> float:
        """How far off the current belief is from ground truth right now."""
        return abs(self.belief.reported_level_percent - self.true_state.level_percent)
