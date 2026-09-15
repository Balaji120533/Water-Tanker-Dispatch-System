"""
Terminal demo for Phase 0.

Usage:
    python demo.py                  interactive: ask for a zone name
    python demo.py <zone>           check one zone directly
    python demo.py --all            forward-chain: list every entitled/high-priority zone
"""

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from logic import Term
from parser import parse_kb
from engine import Engine

KB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.txt")
REPORTS_PATH = os.path.join(os.path.dirname(__file__), "zone_reports.txt")


def load_engine() -> Engine:
    clauses = parse_kb(KB_PATH) + parse_kb(REPORTS_PATH)
    return Engine(clauses)


def check_zone(engine: Engine, zone: str) -> None:
    print(f"\n=== Checking zone: {zone} ===\n")

    entitled_results = engine.backward_chain(Term("entitled", (zone,)))
    priority_results = engine.backward_chain(Term("high_priority", (zone,)))

    if not entitled_results:
        print(f"Result: {zone} is NOT entitled (no proof found).")
        return

    print(f"Result: {zone} IS entitled.")
    print(f"\nProof ({len(entitled_results)} way(s) to prove it):")
    for i, (_, proof) in enumerate(entitled_results, 1):
        print(f"\n-- Derivation {i} --")
        print(proof.pretty())

    if priority_results:
        print(f"\nResult: {zone} is HIGH PRIORITY.")
        print(f"\nProof:")
        print(priority_results[0][1].pretty())
    else:
        print(f"\nResult: {zone} is entitled but NOT high priority.")


def show_all(engine: Engine) -> None:
    facts = engine.forward_chain()
    entitled = sorted(f.args[0] for f in facts if f.predicate == "entitled")
    high_priority = sorted(f.args[0] for f in facts if f.predicate == "high_priority")

    print("\n=== Forward chaining: all derived facts ===\n")
    print(f"Entitled zones ({len(entitled)}):")
    for z in entitled:
        marker = " [HIGH PRIORITY]" if z in high_priority else ""
        print(f"  - {z}{marker}")

    all_zones = sorted(
        set(
            c.head.args[0]
            for c in engine.clauses
            if c.head.predicate == "tank_level" and c.is_fact()
        )
    )
    not_entitled = [z for z in all_zones if z not in entitled]
    if not_entitled:
        print(f"\nNot entitled ({len(not_entitled)}):")
        for z in not_entitled:
            print(f"  - {z}")


def main():
    engine = load_engine()

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        show_all(engine)
        return

    if len(sys.argv) > 1:
        zone = sys.argv[1]
    else:
        zone = input("Enter zone name (e.g. tondiarpet): ").strip()

    check_zone(engine, zone)


if __name__ == "__main__":
    main()
