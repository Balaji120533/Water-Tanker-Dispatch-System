"""
Parse a volunteer's plain Tamil/English message into structured facts for
Phase 0's entitlement engine.

RULE 2 BOUNDARY: this module's ONLY output is a validated JSON object of
facts (zone_name, tank_level, days_since_delivery). It NEVER decides
entitlement or priority -- that decision is made exclusively by Phase 0's
logic engine, given these facts as input, exactly like the volunteer
dropdown in Phase 4 does. The LLM here plays the same role a form field
does: it extracts values, nothing more. If the model's output doesn't pass
validation, we refuse to use it rather than guess.
"""

from __future__ import annotations
import json
import re
from llm_client import chat

VALID_ZONES = [
    "teynampet", "tondiarpet", "thiruvotriyur", "manali",
    "royapuram", "kodambakkam", "alandur", "perungudi",
]

SYSTEM_PROMPT = f"""You extract structured facts from a citizen's message about their \
neighborhood's water tank. You do NOT decide whether they get water, you do NOT give \
opinions or advice, and you do NOT invent information the message doesn't contain.

Valid zone names (choose the closest match, or null if none match): {VALID_ZONES}

Respond with ONLY a JSON object, no other text, in this exact shape:
{{"zone_name": <one of the valid zones above, or null>, "tank_level_percent": <integer 0-100, or null if not mentioned>, "days_since_delivery": <integer >= 0, or null if not mentioned>}}

If the message describes severity in words ("empty", "almost dry", "very low", "fine", \
"full") instead of a number, estimate a reasonable percentage. If information is missing, \
use null for that field -- do not guess a specific number you were not given any basis for.
"""


class ParseError(Exception):
    pass


def _extract_json(text: str) -> dict:
    """Model output should be pure JSON, but strip code fences defensively."""
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ParseError(f"No JSON object found in model output: {text!r}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ParseError(f"Model output was not valid JSON: {e}")


def _validate(data: dict) -> dict:
    """
    Validate every field before it is trusted. This is the actual Rule-2
    enforcement point: nothing from the model reaches the entitlement
    engine without passing every check here.
    """
    if not isinstance(data, dict):
        raise ParseError("Model output was not a JSON object")

    zone = data.get("zone_name")
    if zone is not None and zone not in VALID_ZONES:
        raise ParseError(f"Model returned an unknown zone: {zone!r}")

    level = data.get("tank_level_percent")
    if level is not None:
        if not isinstance(level, (int, float)) or not (0 <= level <= 100):
            raise ParseError(f"tank_level_percent out of range or wrong type: {level!r}")
        level = int(level)

    days = data.get("days_since_delivery")
    if days is not None:
        if not isinstance(days, (int, float)) or days < 0:
            raise ParseError(f"days_since_delivery invalid: {days!r}")
        days = int(days)

    return {"zone_name": zone, "tank_level_percent": level, "days_since_delivery": days}


def parse_message(message: str) -> dict:
    """
    Parse a plain-language message into validated structured facts.
    Raises ParseError if the model's output can't be trusted -- callers
    must handle this (e.g. ask the volunteer to use the dropdown form
    instead), never silently fall back to a guessed value.
    """
    raw = chat(message, system=SYSTEM_PROMPT)
    data = _extract_json(raw)
    return _validate(data)
