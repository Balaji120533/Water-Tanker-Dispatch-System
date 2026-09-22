"""
Terminal demo: a stale belief corrected mid-day (CLAUDE.md Phase 5
deliverable). Shows the true level draining unseen, the system continuing
to act on a stale belief, and a fresh report triggering a replan.

Usage: python demo_partial_observability.py
"""

from __future__ import annotations
from partial_observability import PartialObservabilitySimulator


def main():
    print("=== Partial observability demo: manali ===\n")
    print("Starts at 45% (not entitled -- threshold is <30%).")
    print(f"True level drains at {5.0}%/hour, unseen by the dispatch system.\n")

    sim = PartialObservabilitySimulator("manali", initial_level_percent=45.0)

    print(f"t=0h: belief={sim.belief.reported_level_percent}%, "
          f"true={sim.true_state.level_percent}% (in sync)\n")

    sim.advance_to(4.0)
    print(f"t=4h: belief STILL={sim.belief.reported_level_percent}% (no new report received), "
          f"but true level has drained to {sim.true_state.level_percent}%")
    print(f"       belief-vs-reality gap: {sim.belief_vs_reality_gap():.1f} percentage points")
    print("       If the dispatcher checked entitlement right now using the stale belief,")
    print("       manali would incorrectly show as NOT entitled.\n")

    print("t=4h: a fresh volunteer report arrives, reflecting reality...")
    result = sim.new_report_arrives(reported_level_percent=sim.true_state.level_percent)

    print(f"\n  Old (stale) belief: {result['old_belief_level']}% -> decision: {result['old_decision']}")
    print(f"  New (corrected) belief: {sim.belief.reported_level_percent}% -> decision: {result['new_decision']}")
    print(f"  Decision changed by replanning: {result['decision_changed']}")

    print("\n=== Full event log ===")
    print(sim.log.pretty())


if __name__ == "__main__":
    main()
