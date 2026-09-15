"""
Core representation for first-order-logic facts and definite clauses.

Everything downstream (unification, backward chaining, forward chaining)
operates on the three types defined here: Variable, Term (a predicate
applied to arguments), and Clause (a Horn clause: head :- body).
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Variable:
    """A logic variable, e.g. Zone, Level, Days. Matched by unification."""
    name: str

    def __repr__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Term:
    """
    A predicate applied to arguments, e.g. tank_level(kolathur, 15) or
    entitled(Zone). Arguments are either constants (str/int) or Variables.

    This same class represents both ground facts (no Variables in args)
    and the head/body atoms inside rules (which do contain Variables).
    """
    predicate: str
    args: tuple = field(default_factory=tuple)

    def __repr__(self) -> str:
        if not self.args:
            return self.predicate
        return f"{self.predicate}({', '.join(str(a) for a in self.args)})"

    def is_ground(self) -> bool:
        """True if no argument is a Variable — i.e. this is a concrete fact."""
        return not any(isinstance(a, Variable) for a in self.args)


@dataclass(frozen=True)
class Clause:
    """
    A definite (Horn) clause: head :- body1, body2, ...
    An empty body means this clause is a plain fact.
    """
    head: Term
    body: tuple = field(default_factory=tuple)

    def is_fact(self) -> bool:
        return len(self.body) == 0

    def __repr__(self) -> str:
        if self.is_fact():
            return f"{self.head}."
        body_str = ", ".join(str(b) for b in self.body)
        return f"{self.head} :- {body_str}."
