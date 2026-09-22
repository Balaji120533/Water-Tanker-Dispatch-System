"""
Generate a plain-language explanation of an allocation decision.

RULE 2 BOUNDARY: this module NEVER decides anything and NEVER introduces a
reason the logic engine didn't already establish. Its only input is a
proof tree / derivation STRING already produced by Phase 0's backward
chaining (engine.py's ProofNode.pretty()) -- real output the entitlement
engine already committed to. The LLM's job is purely stylistic: turn that
technical derivation into a sentence a non-technical reader can follow,
without adding, omitting, or reversing any fact in it.
"""

from __future__ import annotations
from llm_client import chat

SYSTEM_PROMPT = """You rewrite a technical logic-engine proof trace into one or two plain \
English sentences for a non-technical reader (a ward volunteer or resident).

Rules you must follow exactly:
- Only restate facts that are literally present in the proof trace given to you.
- Do NOT add reasons, context, or facts that are not in the trace.
- Do NOT change the conclusion (entitled/not entitled, priority/not priority).
- Do NOT give opinions, apologies, or suggestions -- only explain the WHY.
- Keep it to 1-2 short sentences.
"""


def explain_decision(zone_name: str, entitled: bool, high_priority: bool, proof_trace: str) -> str:
    """
    Turn a raw proof trace (from Phase 0's ProofNode.pretty()) into a
    plain-language explanation. If proof_trace is empty (not entitled,
    no proof to explain), returns a fixed, non-LLM message -- there is
    nothing for the model to rephrase in that case.
    """
    if not proof_trace:
        return f"{zone_name} does not currently meet the entitlement criteria based on its reported condition."

    prompt = (
        f"Zone: {zone_name}\n"
        f"Entitled: {entitled}\n"
        f"High priority: {high_priority}\n"
        f"Proof trace from the logic engine:\n{proof_trace}\n\n"
        f"Explain this decision in plain language."
    )
    return chat(prompt, system=SYSTEM_PROMPT).strip()
