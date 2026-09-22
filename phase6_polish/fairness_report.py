"""
Produces the FAIRNESS evidence table (CLAUDE.md Phase 6): a measured
before/after showing that no zone is repeatedly skipped.

Run: python fairness_report.py
"""

from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase1_csp"))

from problem import Tanker  # noqa: E402
from week_simulation import run_week, fairness_report, ALL_ZONES  # noqa: E402

# A strained fleet is used deliberately. With the full 5-tanker fleet the
# supply (102,000L) far exceeds demand (56,000L), every zone is served
# every time, and the fairness question never actually arises -- there is
# nothing to be unfair ABOUT. Cutting to two tankers forces the allocator
# to choose who waits, which is the only condition under which a fairness
# claim can be tested rather than assumed.
STRAINED_FLEET = [Tanker("T1", 9000), Tanker("T2", 9000)]
DAYS = 14


def _row(label: str, rep: dict) -> str:
    return "%-28s %14d %18d %12d" % (
        label,
        len(rep["never_served"]),
        rep["max_skip_streak"],
        rep["spread"],
    )


def main():
    print("=" * 76)
    print("FAIRNESS OVER A SIMULATED %d-DAY WEEK" % DAYS)
    print("=" * 76)
    print()
    print("Fleet: %d tankers (%s) -- deliberately strained so the allocator"
          % (len(STRAINED_FLEET), ", ".join(f"{t.capacity_liters}L" for t in STRAINED_FLEET)))
    print("must choose who waits. Zones: all %d GCC zones." % len(ALL_ZONES))
    print()

    print("%-28s %14s %18s %12s" % ("configuration", "never served", "max skip streak", "spread"))
    print("-" * 76)

    results_off, _, ds_off = run_week(days=DAYS, fairness_soft_constraint=False,
                                      start_level=30, tankers=STRAINED_FLEET)
    rep_off = fairness_report(results_off, ds_off)
    print(_row("hard constraints only", rep_off))

    results_on, _, ds_on = run_week(days=DAYS, fairness_soft_constraint=True,
                                    start_level=30, tankers=STRAINED_FLEET)
    rep_on = fairness_report(results_on, ds_on)
    print(_row("+ fairness soft constraint", rep_on))

    print()
    print("never served    = zones entitled during the week that received no delivery at all")
    print("max skip streak = longest run of consecutive days a zone was entitled but skipped")
    print("spread          = (most deliveries to any zone) - (fewest), lower is more even")
    print()

    if rep_off["never_served"]:
        print("Starved without the soft constraint: %s" % ", ".join(rep_off["never_served"]))
    if rep_on["never_served"]:
        print("Starved WITH the soft constraint:    %s" % ", ".join(rep_on["never_served"]))
    else:
        print("With the soft constraint, every entitled zone received water at least once.")

    print()
    print("Per-zone deliveries (with fairness soft constraint):")
    for zone in sorted(ALL_ZONES, key=lambda z: rep_on["times_served"][z]):
        print("  %-18s served %d  (entitled on %d days, skipped %d)"
              % (zone, rep_on["times_served"][zone], rep_on["times_entitled"][zone],
                 rep_on["times_skipped"][zone]))


if __name__ == "__main__":
    main()
