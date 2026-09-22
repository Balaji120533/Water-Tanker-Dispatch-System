"""
Reproducible demo script (CLAUDE.md Phase 6).

Runs every claim the project makes, in order, from a clean checkout --
so a reviewer can verify the whole system without clicking through three
web UIs.

Run: python scripts/demo.py
     python scripts/demo.py --skip-slow     (skips the OSM road network)
"""

from __future__ import annotations
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def banner(n: int, title: str) -> None:
    print()
    print("=" * 78)
    print(f"  {n}. {title}")
    print("=" * 78)


def run_python(argv: list[str], cwd: str | None = None) -> bool:
    """
    Run `python <argv>` and show its output. Returns False if it failed.

    Output is captured and re-printed rather than inherited, because when
    this script's own stdout is a pipe (piping to `tail`, or a CI log) the
    children buffer their output and it can be lost or reordered -- a demo
    that prints nothing proves nothing. PYTHONUNBUFFERED keeps the child's
    own ordering intact.
    """
    cmd = [sys.executable] + argv
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    result = subprocess.run(
        cmd, cwd=cwd or ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stdout.flush()
    if result.returncode != 0:
        print(f"\n  !! {' '.join(argv)} exited with code {result.returncode}")
        return False
    return True


def run(script: str, args: list[str] | None = None, cwd: str | None = None) -> bool:
    """Run one demo script by path."""
    return run_python([script] + (args or []), cwd=cwd)


def main() -> int:
    skip_slow = "--skip-slow" in sys.argv
    t0 = time.time()
    failures: list[str] = []

    print("Water Tanker Dispatch System -- full demo")
    print("Every number printed below is produced live, not quoted from a doc.")

    # ---- Unit IV: logic ------------------------------------------------
    banner(1, "ENTITLEMENT (Unit IV: FOL, unification, backward chaining)")
    print("One zone, with the derivation that justifies the decision.\n")
    if not run(os.path.join("phase0_entitlement", "demo.py"), ["tondiarpet"]):
        failures.append("entitlement demo")

    banner(2, "FORWARD CHAINING (Unit IV: derive every entitled zone)")
    if not run(os.path.join("phase0_entitlement", "demo.py"), ["--all"]):
        failures.append("forward chaining demo")

    # ---- Unit III: CSP -------------------------------------------------
    banner(3, "CSP BENCHMARKS (Unit III: AC-3, MRV, degree, LCV)")
    print("Satisfaction vs optimisation search -- see the commentary under")
    print("each table for why the node counts differ so sharply.\n")
    if not run(os.path.join("phase6_polish", "benchmark_report.py")):
        failures.append("benchmark report")

    banner(4, "FAIRNESS (Unit III: soft constraints over a simulated fortnight)")
    print("The headline claim, measured rather than asserted.\n")
    if not run(os.path.join("phase6_polish", "fairness_report.py")):
        failures.append("fairness report")

    # ---- Unit II: search under uncertainty -----------------------------
    banner(5, "PARTIAL OBSERVABILITY (Units I & II: belief state, replanning)")
    print("A stale belief corrected mid-day, flipping the decision.\n")
    if not run(os.path.join("phase5_agentic", "demo_partial_observability.py")):
        failures.append("partial observability demo")

    # ---- Unit II: routing (slow: downloads the road network) -----------
    banner(6, "ROUTING ON REAL ROADS (Unit II: A* with haversine heuristic)")
    if skip_slow:
        print("Skipped (--skip-slow). Run without the flag to fetch the")
        print("Chennai road network and render route_map.html.")
    else:
        print("First run downloads the Chennai drive network (~100s) and caches it.\n")
        if not run("visualize.py", cwd=os.path.join(ROOT, "phase2_routing")):
            failures.append("routing visualisation")

    # ---- Tests ---------------------------------------------------------
    banner(7, "TEST SUITE")
    if not run_python(["-m", "pytest", "-q",
                       "phase0_entitlement/tests", "phase1_csp/tests", "phase2_routing/tests",
                       "phase3_repair/tests", "phase5_agentic/tests", "phase6_polish/tests"]):
        failures.append("test suite")

    # ---- Summary -------------------------------------------------------
    print()
    print("=" * 78)
    if failures:
        print("  DEMO FINISHED WITH FAILURES: " + ", ".join(failures))
    else:
        print("  DEMO COMPLETE -- every claim above ran successfully.")
    print("  Elapsed: %.0fs" % (time.time() - t0))
    print("=" * 78)
    print()
    print("Not covered here (they need the web UIs):")
    print("  - volunteer chat, driver map, and live repair on the dashboard")
    print("  - start them with:  npm run dev")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
