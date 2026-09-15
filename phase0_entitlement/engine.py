"""
Inference engine: backward chaining (with proof tree) and forward chaining.

Design note: this engine works over a small set of BUILTIN_PREDICATES for
arithmetic (lt30, gt3, lt10) instead of requiring the knowledge base to
enumerate "lt30(5)." as a fact for every possible number. Everything else
(entitled, high_priority, tank_level, days_since_delivery,
has_critical_facility) is resolved purely from the KB via unification.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from logic import Variable, Term, Clause
from unify import unify, substitute, Substitution

BUILTIN_PREDICATES = {
    "lt30": lambda level: level < 30,
    "gt3": lambda days: days > 3,
    "lt10": lambda level: level < 10,
}

_counter = [0]


def _fresh(term: Term) -> Term:
    """
    Rename all variables in `term` to fresh, globally-unique names.

    Needed because the same rule (e.g. entitled(Zone) :- ...) gets reused
    across many different queries/subgoals in one proof. Without renaming,
    a variable named Zone from one use of the rule could accidentally get
    unified with a binding left over from a different use of the same rule.
    """
    mapping: dict[Variable, Variable] = {}

    def rename(x):
        if isinstance(x, Variable):
            if x not in mapping:
                _counter[0] += 1
                mapping[x] = Variable(f"{x.name}_{_counter[0]}")
            return mapping[x]
        return x

    return Term(term.predicate, tuple(rename(a) for a in term.args))


def _fresh_clause(clause: Clause) -> Clause:
    mapping: dict[Variable, Variable] = {}

    def rename(x):
        if isinstance(x, Variable):
            if x not in mapping:
                _counter[0] += 1
                mapping[x] = Variable(f"{x.name}_{_counter[0]}")
            return mapping[x]
        return x

    new_head = Term(clause.head.predicate, tuple(rename(a) for a in clause.head.args))
    new_body = tuple(
        Term(b.predicate, tuple(rename(a) for a in b.args)) for b in clause.body
    )
    return Clause(new_head, new_body)


@dataclass
class ProofNode:
    """One node in a proof tree: the goal proved, and the children that proved it."""
    goal: Term
    children: list["ProofNode"] = field(default_factory=list)
    via_rule: str | None = None  # human-readable clause used, or 'builtin'/'fact'

    def pretty(self, indent: int = 0) -> str:
        pad = "  " * indent
        line = f"{pad}{self.goal}"
        if self.via_rule:
            line += f"   [{self.via_rule}]"
        lines = [line]
        for child in self.children:
            lines.append(child.pretty(indent + 1))
        return "\n".join(lines)


class Engine:
    def __init__(self, clauses: list[Clause]):
        self.clauses = clauses

    # ---------------------------------------------------------------
    # BACKWARD CHAINING
    # ---------------------------------------------------------------
    def backward_chain(self, goal: Term):
        """
        Prove `goal` against the KB. Returns a list of (substitution, proof)
        pairs — one per way the goal can be proved (there can be more than
        one, e.g. two different rules both make a zone entitled).
        Empty list means the goal could not be proved (negation as failure).
        """
        return self._prove(goal, {})

    def _prove(self, goal: Term, subst: Substitution):
        goal = substitute(goal, subst)

        # Case 1: builtin arithmetic predicate (lt30, gt3, lt10)
        if goal.predicate in BUILTIN_PREDICATES:
            arg = goal.args[0]
            if isinstance(arg, Variable):
                return []  # can't evaluate an unbound variable
            if BUILTIN_PREDICATES[goal.predicate](arg):
                return [(subst, ProofNode(goal, via_rule="builtin arithmetic check"))]
            return []

        # Case 2: try every clause whose head might match this goal
        results = []
        for clause in self.clauses:
            fresh = _fresh_clause(clause)
            new_subst = unify(goal, fresh.head, subst)
            if new_subst is None:
                continue

            if fresh.is_fact():
                proof = ProofNode(substitute(goal, new_subst), via_rule="fact in KB")
                results.append((new_subst, proof))
                continue

            # Recursively prove every subgoal in the body, threading the
            # substitution through so earlier subgoals constrain later ones.
            for final_subst, child_proofs in self._prove_body(fresh.body, new_subst):
                proof = ProofNode(
                    substitute(goal, final_subst),
                    children=child_proofs,
                    via_rule=str(clause),
                )
                results.append((final_subst, proof))

        return results

    def _prove_body(self, body: tuple, subst: Substitution):
        """
        Prove a conjunction of subgoals left-to-right. Yields
        (substitution, [ProofNode, ...]) for every combination that proves
        the whole body — this is where backtracking across subgoals happens.
        """
        if not body:
            yield subst, []
            return

        first, rest = body[0], body[1:]
        for new_subst, first_proof in self._prove(first, subst):
            for final_subst, rest_proofs in self._prove_body(rest, new_subst):
                yield final_subst, [first_proof] + rest_proofs

    # ---------------------------------------------------------------
    # FORWARD CHAINING
    # ---------------------------------------------------------------
    def forward_chain(self) -> set[Term]:
        """
        Derive every fact entailed by the KB (naive forward chaining: keep
        applying rules until no new fact is produced — a fixpoint).
        Returns the full set of derived ground facts, including the
        original facts.
        """
        known: set[Term] = {c.head for c in self.clauses if c.is_fact()}
        rules = [c for c in self.clauses if not c.is_fact()]

        changed = True
        while changed:
            changed = False
            snapshot = set(known)  # freeze facts used to satisfy bodies this pass
            new_facts = set()
            for rule in rules:
                for subst in self._satisfy_body(rule.body, snapshot):
                    new_fact = substitute(rule.head, subst)
                    if new_fact.is_ground() and new_fact not in known:
                        new_facts.add(new_fact)
            if new_facts:
                known |= new_facts
                changed = True
        return known

    def _satisfy_body(self, body: tuple, known: set[Term]):
        """
        Yield every substitution that makes every atom in `body` true,
        given the currently-known ground facts (plus builtin arithmetic).
        """
        yield from self._satisfy_from(body, known, {})

    def _satisfy_from(self, body: tuple, known: set[Term], subst: Substitution):
        if not body:
            yield subst
            return

        goal = substitute(body[0], subst)
        rest = body[1:]

        if goal.predicate in BUILTIN_PREDICATES:
            arg = goal.args[0]
            if not isinstance(arg, Variable) and BUILTIN_PREDICATES[goal.predicate](arg):
                yield from self._satisfy_from(rest, known, subst)
            return

        for fact in known:
            new_subst = unify(goal, fact, subst)
            if new_subst is not None:
                yield from self._satisfy_from(rest, known, new_subst)
