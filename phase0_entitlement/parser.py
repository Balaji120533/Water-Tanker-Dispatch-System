"""
Parses knowledge_base.txt into Clause objects.

Kept deliberately small and regex-free (hand-rolled tokenizing on top of
str.split) so every step is easy to explain line-by-line in teach-back.
"""

from __future__ import annotations
from logic import Variable, Term, Clause


def _parse_arg(token: str):
    """A token is a Variable if it starts with an uppercase letter, else a constant."""
    token = token.strip()
    if token[0].isupper():
        return Variable(token)
    if token.lstrip("-").isdigit():
        return int(token)
    return token  # lowercase atom, e.g. a zone name


def _parse_term(text: str) -> Term:
    text = text.strip()
    if "(" not in text:
        return Term(text, ())
    predicate, rest = text.split("(", 1)
    rest = rest.rstrip(")")
    args = tuple(_parse_arg(a) for a in rest.split(",")) if rest.strip() else ()
    return Term(predicate.strip(), args)


def _strip_comment(line: str) -> str:
    if "#" in line:
        line = line[: line.index("#")]
    return line.strip()


def parse_kb(path: str) -> list[Clause]:
    """
    Read a knowledge-base text file and return a list of Clause objects.
    Statements are terminated by '.' and may span multiple physical lines
    (we join lines until a '.' is seen, so wrapping a long rule is fine).
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    lines = [_strip_comment(l) for l in raw.splitlines()]
    text = " ".join(l for l in lines if l)

    statements = [s.strip() for s in text.split(".") if s.strip()]

    clauses = []
    for stmt in statements:
        if ":-" in stmt:
            head_text, body_text = stmt.split(":-", 1)
            head = _parse_term(head_text)
            body = tuple(_parse_term(t) for t in _split_body(body_text))
            clauses.append(Clause(head, body))
        else:
            clauses.append(Clause(_parse_term(stmt), ()))
    return clauses


def _split_body(body_text: str) -> list[str]:
    """
    Split a rule body on commas that are NOT inside parentheses, so that
    tank_level(Zone, Level), lt30(Level) splits into two terms, not four.
    """
    parts = []
    depth = 0
    current = []
    for ch in body_text:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]
