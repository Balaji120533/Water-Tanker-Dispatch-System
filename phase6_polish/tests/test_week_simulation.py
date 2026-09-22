import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "phase1_csp"))

from problem import Tanker
from week_simulation import (
    run_week, fairness_report, classify, ALL_ZONES, DAILY_DRAIN_PERCENT, REFILL_TO_PERCENT,
)

STRAINED = [Tanker("T1", 9000), Tanker("T2", 9000)]


def test_full_tanks_are_not_entitled():
    levels = {z: 100 for z in ALL_ZONES}
    days = {z: 0 for z in ALL_ZONES}
    entitled, _ = classify(levels, days)
    assert entitled == []


def test_empty_tanks_are_all_entitled():
    levels = {z: 0 for z in ALL_ZONES}
    days = {z: 0 for z in ALL_ZONES}
    entitled, high = classify(levels, days)
    assert set(entitled) == set(ALL_ZONES)
    assert set(high) == set(ALL_ZONES)  # 0% is below the severity threshold too


def test_served_zones_refill_and_unserved_zones_drain():
    results, levels, days_since = run_week(days=3, start_level=25)
    last = results[-1]
    for zone in last.served:
        assert levels[zone] == REFILL_TO_PERCENT
        assert days_since[zone] == 0
    for zone in last.unserved_entitled:
        assert levels[zone] <= last.levels_before[zone] - DAILY_DRAIN_PERCENT + 1


def test_a_zone_is_never_served_without_being_entitled():
    results, _, _ = run_week(days=7, start_level=40)
    for r in results:
        assert set(r.served).issubset(set(r.entitled))


def test_fairness_soft_constraint_removes_starvation_under_strain():
    # The headline Phase 6 claim. With a strained fleet the plain allocator
    # leaves some zones entirely unserved; the soft constraint must not.
    _, _, ds_off = run_week(days=14, fairness_soft_constraint=False, start_level=30, tankers=STRAINED)
    res_off, _, _ = run_week(days=14, fairness_soft_constraint=False, start_level=30, tankers=STRAINED)
    rep_off = fairness_report(res_off, ds_off)

    res_on, _, ds_on = run_week(days=14, fairness_soft_constraint=True, start_level=30, tankers=STRAINED)
    rep_on = fairness_report(res_on, ds_on)

    assert len(rep_off["never_served"]) > 0, "baseline should starve someone, else the test proves nothing"
    assert rep_on["never_served"] == []
    assert rep_on["max_skip_streak"] < rep_off["max_skip_streak"]


def test_fairness_soft_constraint_narrows_the_spread():
    res_off, _, ds_off = run_week(days=14, fairness_soft_constraint=False, start_level=30, tankers=STRAINED)
    res_on, _, ds_on = run_week(days=14, fairness_soft_constraint=True, start_level=30, tankers=STRAINED)
    assert fairness_report(res_on, ds_on)["spread"] <= fairness_report(res_off, ds_off)["spread"]


def test_report_counts_are_internally_consistent():
    results, _, ds = run_week(days=7, start_level=30)
    rep = fairness_report(results, ds)
    for zone in ALL_ZONES:
        # every day a zone was entitled it was either served or skipped
        assert rep["times_entitled"][zone] == rep["times_served"][zone] + rep["times_skipped"][zone]
