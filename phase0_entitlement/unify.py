"""
Unification with occurs-check.

Unification asks: given two terms (possibly containing variables), is there
a substitution of variables -> values that makes them syntactically
identical? If yes, return the substitution (a dict). If no, return None.

This is the single operation that both backward chaining and forward
chaining are built on top of.
"""

from __future__ import annotations
from typing import Optional
from logic import Variable, Term

Substitution = dict  # Variable -> constant or Variable


def walk(x, subst: Substitution):
    """
    Follow a chain of variable bindings until we reach a non-variable or an
    unbound variable. E.g. if subst = {X: Y, Y: 5}, walk(X, subst) -> 5.
    """
    while isinstance(x, Variable) and x in subst:
        x = subst[x]
    return x


def occurs_check(var: Variable, x, subst: Substitution) -> bool:
    """
    True if `var` occurs inside `x` (after resolving bindings already in
    subst). Prevents binding X = f(X), which would create an infinite term.

    Not usually triggerable by our flat zone-dispatch predicates (no nested
    terms), but it is included because it is required for unification to be
    correct in general, and because the phase brief explicitly calls it out
    as a thing to point at during teach-back.
    """
    x = walk(x, subst)
    if var == x:
        return True
    if isinstance(x, Term):
        return any(occurs_check(var, arg, subst) for arg in x.args)
    return False


def unify_var(var: Variable, x, subst: Substitution) -> Optional[Substitution]:
    if var in subst:
        return unify(subst[var], x, subst)
    if isinstance(x, Variable) and x in subst:
        return unify(var, subst[x], subst)
    if occurs_check(var, x, subst):
        return None
    new_subst = dict(subst)
    new_subst[var] = x
    return new_subst


def unify(a, b, subst: Optional[Substitution] = None) -> Optional[Substitution]:
    """
    Attempt to unify `a` and `b` under the current substitution `subst`.
    Returns the extended substitution on success, or None on failure.

    Handles four cases: both Terms (recurse arg-by-arg after matching
    predicate/arity), either side a Variable (delegate to unify_var), or
    two constants (succeed only if equal).
    """
    if subst is None:
        subst = {}

    a = walk(a, subst)
    b = walk(b, subst)

    if a == b:
        return subst

    if isinstance(a, Variable):
        return unify_var(a, b, subst)
    if isinstance(b, Variable):
        return unify_var(b, a, subst)

    if isinstance(a, Term) and isinstance(b, Term):
        if a.predicate != b.predicate or len(a.args) != len(b.args):
            return None
        for arg_a, arg_b in zip(a.args, b.args):
            subst = unify(arg_a, arg_b, subst)
            if subst is None:
                return None
        return subst

    return None  # constants that differ, or mismatched types


def substitute(term: Term, subst: Substitution) -> Term:
    """Apply a substitution to a term, replacing bound variables with their values."""
    new_args = tuple(walk(arg, subst) for arg in term.args)
    return Term(term.predicate, new_args)
