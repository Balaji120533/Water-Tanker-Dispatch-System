import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logic import Variable, Term
from unify import unify, occurs_check


def test_unify_identical_constants():
    assert unify(Term("entitled", ("adyar",)), Term("entitled", ("adyar",))) == {}


def test_unify_different_constants_fails():
    assert unify(Term("entitled", ("adyar",)), Term("entitled", ("manali",))) is None


def test_unify_variable_binds_to_constant():
    X = Variable("X")
    subst = unify(Term("entitled", (X,)), Term("entitled", ("adyar",)))
    assert subst == {X: "adyar"}


def test_unify_mismatched_predicate_fails():
    assert unify(Term("entitled", ("adyar",)), Term("high_priority", ("adyar",))) is None


def test_unify_mismatched_arity_fails():
    assert unify(Term("p", ("a",)), Term("p", ("a", "b"))) is None


def test_unify_two_variables_same_goal_consistent():
    X, Y = Variable("X"), Variable("Y")
    subst = unify(Term("p", (X, X)), Term("p", ("a", Y)))
    assert subst is not None
    # X bound to 'a', Y must walk to 'a' too via the chain
    from unify import walk
    assert walk(X, subst) == "a"
    assert walk(Y, subst) == "a"


def test_occurs_check_prevents_self_reference():
    X = Variable("X")
    nested = Term("f", (X,))
    # trying to bind X = f(X) should be rejected
    assert occurs_check(X, nested, {}) is True


def test_occurs_check_allows_unrelated_binding():
    X, Y = Variable("X"), Variable("Y")
    assert occurs_check(X, Term("f", (Y,)), {}) is False
