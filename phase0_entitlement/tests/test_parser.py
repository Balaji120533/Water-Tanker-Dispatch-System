import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logic import Variable
from parser import parse_kb

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge_base.txt")
REPORTS_PATH = os.path.join(os.path.dirname(__file__), "..", "zone_reports.txt")


def test_kb_parses_without_error():
    clauses = parse_kb(KB_PATH)
    assert len(clauses) > 0


def test_kb_has_expected_rule_heads():
    clauses = parse_kb(KB_PATH)
    heads = {c.head.predicate for c in clauses if not c.is_fact()}
    assert "entitled" in heads
    assert "high_priority" in heads


def test_rule_body_parsed_as_multiple_terms():
    clauses = parse_kb(KB_PATH)
    entitled_rules = [c for c in clauses if c.head.predicate == "entitled"]
    assert len(entitled_rules) == 2
    level_rule = next(r for r in entitled_rules if r.body[0].predicate == "tank_level")
    assert len(level_rule.body) == 2
    assert level_rule.body[1].predicate == "lt30"


def test_rule_variables_parsed_as_variable_type():
    clauses = parse_kb(KB_PATH)
    entitled_rules = [c for c in clauses if c.head.predicate == "entitled"]
    assert isinstance(entitled_rules[0].head.args[0], Variable)


def test_reports_parse_as_ground_facts():
    facts = parse_kb(REPORTS_PATH)
    assert all(c.is_fact() for c in facts)
    assert all(c.head.is_ground() for c in facts)


def test_reports_contain_tondiarpet_facility_fact():
    facts = parse_kb(REPORTS_PATH)
    facility_facts = [f for f in facts if f.head.predicate == "has_critical_facility"]
    names = {f.head.args[0] for f in facility_facts}
    assert "tondiarpet" in names
