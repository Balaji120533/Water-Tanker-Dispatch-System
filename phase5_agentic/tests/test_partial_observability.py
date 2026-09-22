import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from partial_observability import PartialObservabilitySimulator, TrueZoneState, Belief, DRAIN_RATE_PERCENT_PER_HOUR
from engine_bridge import decide


def test_true_state_drains_at_fixed_rate():
    state = TrueZoneState("manali", 50.0)
    state.drain(hours=2.0)
    assert state.level_percent == 50.0 - 2 * DRAIN_RATE_PERCENT_PER_HOUR


def test_true_state_never_drains_below_zero():
    state = TrueZoneState("manali", 3.0)
    state.drain(hours=10.0)
    assert state.level_percent == 0.0


def test_belief_does_not_change_on_time_advance_alone():
    sim = PartialObservabilitySimulator("manali", initial_level_percent=50.0)
    sim.advance_to(5.0)
    assert sim.belief.reported_level_percent == 50.0  # belief is stale, unchanged
    assert sim.true_state.level_percent < 50.0  # but reality has moved on


def test_belief_vs_reality_gap_grows_with_time():
    sim = PartialObservabilitySimulator("manali", initial_level_percent=50.0)
    gap_at_start = sim.belief_vs_reality_gap()
    sim.advance_to(3.0)
    gap_later = sim.belief_vs_reality_gap()
    assert gap_later > gap_at_start


def test_new_report_updates_belief_to_reported_value():
    sim = PartialObservabilitySimulator("manali", initial_level_percent=50.0)
    sim.advance_to(4.0)
    sim.new_report_arrives(reported_level_percent=25.0)
    assert sim.belief.reported_level_percent == 25.0
    assert sim.belief.reported_at_hour == 4.0


def test_stale_belief_corrected_mid_day_changes_decision():
    """
    The core Phase 5 demo: a zone starts at a comfortable level (not
    entitled). Time passes, the true level drains below the entitlement
    threshold, but the belief is stale and still says "comfortable" -- so
    if asked right now, the system would (wrongly) say not entitled. A
    fresh report arrives reflecting the drained level, and replanning
    correctly flips the decision to entitled.
    """
    sim = PartialObservabilitySimulator("manali", initial_level_percent=45.0)  # not entitled (>=30)
    assert decide("manali", sim.belief.reported_level_percent) == "not_entitled"

    sim.advance_to(4.0)  # 45 - 4*5 = 25% true level now, but belief still says 45%
    assert sim.true_state.level_percent == 25.0
    assert sim.belief.reported_level_percent == 45.0  # stale belief unaware of the drain

    result = sim.new_report_arrives(reported_level_percent=25.0)  # fresh report reflects reality

    assert result["old_decision"] == "not_entitled"
    assert result["new_decision"] == "entitled"
    assert result["decision_changed"] is True
    assert result["staleness_hours"] == 4.0


def test_replan_logged_only_when_decision_actually_changes():
    sim = PartialObservabilitySimulator("manali", initial_level_percent=45.0)
    sim.advance_to(1.0)
    # small drain, 45 -> 40, still not entitled either way -- no replan-worthy change
    sim.new_report_arrives(reported_level_percent=40.0)
    replan_events = [e for e in sim.log.events if e["kind"] == "replan"]
    assert replan_events == []


def test_replan_logged_when_decision_changes():
    sim = PartialObservabilitySimulator("manali", initial_level_percent=45.0)
    sim.advance_to(4.0)
    sim.new_report_arrives(reported_level_percent=25.0)
    replan_events = [e for e in sim.log.events if e["kind"] == "replan"]
    assert len(replan_events) == 1


def test_advance_to_rejects_moving_backward():
    sim = PartialObservabilitySimulator("manali", initial_level_percent=45.0)
    sim.advance_to(5.0)
    try:
        sim.advance_to(2.0)
        assert False, "expected ValueError"
    except ValueError:
        pass
