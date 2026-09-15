import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logic import Term
from parser import parse_kb
from engine import Engine

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge_base.txt")
REPORTS_PATH = os.path.join(os.path.dirname(__file__), "..", "zone_reports.txt")


def make_engine():
    return Engine(parse_kb(KB_PATH) + parse_kb(REPORTS_PATH))


# --- Backward chaining --------------------------------------------------

def test_low_level_zone_is_entitled():
    # teynampet: tank_level 5 (<30) -> entitled
    engine = make_engine()
    results = engine.backward_chain(Term("entitled", ("teynampet",)))
    assert len(results) >= 1


def test_stale_delivery_zone_is_entitled_even_if_level_ok():
    # kodambakkam: tank_level 40 (not <30), days_since_delivery 6 (>3) -> entitled
    engine = make_engine()
    results = engine.backward_chain(Term("entitled", ("kodambakkam",)))
    assert len(results) >= 1


def test_healthy_zone_is_not_entitled():
    # ambattur: tank_level 70, days_since_delivery 0 -> neither condition holds
    engine = make_engine()
    results = engine.backward_chain(Term("entitled", ("ambattur",)))
    assert results == []


def test_severe_shortage_is_high_priority():
    # tondiarpet: tank_level 8 (<10) and entitled -> high_priority
    engine = make_engine()
    results = engine.backward_chain(Term("high_priority", ("tondiarpet",)))
    assert len(results) >= 1


def test_facility_zone_that_is_entitled_is_high_priority():
    # tondiarpet also has a critical facility -> second, independent proof path
    engine = make_engine()
    results = engine.backward_chain(Term("high_priority", ("tondiarpet",)))
    rules_used = {proof.via_rule for _, proof in results}
    assert len(rules_used) == 2  # both the severity rule and facility rule fire


def test_facility_without_entitlement_is_not_high_priority():
    # adyar has a critical facility but level 80 / days 0 -> not entitled at all,
    # so high_priority must NOT fire just because of the facility.
    engine = make_engine()
    results = engine.backward_chain(Term("high_priority", ("adyar",)))
    assert results == []


def test_entitled_but_not_severe_and_no_facility_is_not_high_priority():
    # royapuram: level 25 (<30, entitled) but not <10, no facility
    engine = make_engine()
    entitled = engine.backward_chain(Term("entitled", ("royapuram",)))
    priority = engine.backward_chain(Term("high_priority", ("royapuram",)))
    assert len(entitled) >= 1
    assert priority == []


def test_proof_tree_bottoms_out_in_facts_and_builtins():
    engine = make_engine()
    _, proof = engine.backward_chain(Term("entitled", ("teynampet",)))[0]

    def leaves(node):
        if not node.children:
            return [node.via_rule]
        out = []
        for c in node.children:
            out += leaves(c)
        return out

    for via in leaves(proof):
        assert via in ("fact in KB", "builtin arithmetic check")


# --- Forward chaining ----------------------------------------------------

def test_forward_chain_matches_backward_chain_for_entitlement():
    engine = make_engine()
    derived = engine.forward_chain()
    forward_entitled = {f.args[0] for f in derived if f.predicate == "entitled"}

    all_zones = {
        c.head.args[0]
        for c in engine.clauses
        if c.head.predicate == "tank_level" and c.is_fact()
    }
    backward_entitled = {
        z for z in all_zones if engine.backward_chain(Term("entitled", (z,)))
    }

    assert forward_entitled == backward_entitled


def test_forward_chain_derives_high_priority_subset_of_entitled():
    engine = make_engine()
    derived = engine.forward_chain()
    entitled = {f.args[0] for f in derived if f.predicate == "entitled"}
    high_priority = {f.args[0] for f in derived if f.predicate == "high_priority"}
    assert high_priority.issubset(entitled)
