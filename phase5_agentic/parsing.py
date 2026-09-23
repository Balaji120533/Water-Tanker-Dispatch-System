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
from zone_registry import ZONES, ZONE_BY_KEY, resolve_place, zone_from_numbers

# All 15 Chennai Metrowater zones. Earlier this held only the 8 zones in
# today's schedule, which meant a volunteer from any other zone (Anna Nagar,
# Adyar...) could not even REPORT -- the parser was quietly pre-deciding
# who could ask for water. Entitlement is the logic engine's call (Rule 2),
# so every zone must be reportable.
VALID_ZONES = [z.key for z in ZONES]

_ZONE_MENU = ", ".join(f'"{z.key}" ({z.name})' for z in ZONES)

SYSTEM_PROMPT = f"""You extract structured facts from a citizen's message about their \
neighborhood's water tank. You do NOT decide whether they get water, you do NOT give \
opinions or advice, and you do NOT invent information the message doesn't contain.

Chennai Metrowater has 15 zones. Valid zone_name values: {_ZONE_MENU}.
Set "zone_name" ONLY when the message names one of these zones itself. If the citizen
names a smaller locality inside a zone (for example "Vadapalani" or "Mylapore"), do NOT
guess which zone it is in -- leave "zone_name" null and put the locality in
"mentioned_place". A lookup table maps localities to zones; you must not.

Respond with ONLY a JSON object, no other text, in this exact shape:
{{"zone_name": <one of the valid zones above, or null>, "tank_level_percent": <integer 0-100, or null if not mentioned>, "days_since_delivery": <integer >= 0, or null if not mentioned>, "mentioned_place": <the place name the citizen actually typed, or null>}}

ABOUT mentioned_place. Set "zone_name" ONLY to a name from the valid list above -- never to
anything else. Separately, if the citizen named ANY place at all (a locality, area, street,
landmark), copy what they typed into "mentioned_place", spelled as they spelled it. Set it
even when it does match a valid zone, and set it even when it does not -- the caller needs
to tell "they named somewhere we do not cover" apart from "they named nowhere at all".
Do not put a place in "mentioned_place" that the citizen did not actually type.

WORDS TO PERCENTAGES. People almost never give a number. Map descriptive phrases to a
percentage rather than returning null -- returning null for a phrase that clearly conveys
severity is a failure:
  "empty", "no water", "completely dry", "nothing left"        -> 0
  "almost empty", "nearly dry", "about to run out"             -> 5
  "very low", "very little left", "running out"                -> 15
  "low", "getting less", "reducing", "coming down", "less now" -> 25
  "half", "moderate", "okay", "manageable"                     -> 50
  "good", "plenty", "enough"                                   -> 75
  "full", "completely full", "just filled"                     -> 95
Tamil/English mixtures are common: "thanni illa" (no water) -> 0, "konjam thaan iruku"
(only a little) -> 15, "kammi" (less) -> 25. Judge similar phrases by their nearest match
above.

Return null for a field ONLY when the message genuinely says nothing about it -- not merely
because no number was given.
"""

CONTEXT_PROMPT_TEMPLATE = """Facts already established earlier in this conversation:
{known}

The citizen has now said:
{message}

Extract facts from this NEW message. Rules:
- If the new message gives a value for a field, return that value -- even if it differs
  from what is already known (they may be correcting themselves).
- If the new message says nothing about a field, return null for it. Do NOT repeat the
  already-known value; the caller merges them.
- A message like "tank is almost empty" with no area named still gives a tank level.
  A message naming only an area still gives a zone.
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

    # Free text, so it is never trusted as a fact -- it only ever decides
    # WHICH question the bot asks back, and is length-capped so a runaway
    # model response can't be echoed into the chat.
    place = data.get("mentioned_place")
    if place is not None:
        if not isinstance(place, str) or not place.strip():
            place = None
        else:
            place = place.strip()[:40]

    return {
        "zone_name": zone,
        "tank_level_percent": level,
        "days_since_delivery": days,
        "mentioned_place": place,
    }


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


def _describe_known(known: dict) -> str:
    if not known or all(v is None for v in known.values()):
        return "(nothing yet -- this is the start of the conversation)"
    parts = []
    if known.get("zone_name"):
        parts.append(f"area = {known['zone_name']}")
    elif known.get("candidate_zones"):
        # Tell the model a "which one?" question is open, so a reply like
        # "the Kodambakkam one" is read as a zone choice.
        parts.append(f"area = unresolved; the citizen is choosing between zones "
                     f"{known['candidate_zones']} for {known.get('locality')}")
    if known.get("tank_level_percent") is not None:
        parts.append(f"tank level = {known['tank_level_percent']}%")
    if known.get("days_since_delivery") is not None:
        parts.append(f"days since last delivery = {known['days_since_delivery']}")
    return "; ".join(parts)


def parse_in_context(message: str, known: dict) -> dict:
    """
    Parse a message given what the conversation has already established,
    and return the MERGED facts.

    A volunteer naturally spreads information across turns -- "the tank in
    kodambakkam is getting less", then "tank is almost empty". Parsing each
    message in isolation loses the zone from the first and the level from
    the second, so neither turn ever has enough to decide on. Merging is
    done here in Python, not by the model: the model only reports what the
    NEW message says, and values already established are preserved unless
    the new message explicitly overrides them.
    """
    # Answering "which one?" with a bare number ("10", "zone 10") is a zone
    # choice and nothing else. Settled here without the model, which would
    # otherwise also read "10" as a 10% tank level and overwrite the level
    # the volunteer already gave.
    choice = _pick_candidate(message, known)
    if choice is not None:
        return {**known, **choice, "mentioned_place": None}

    prompt = CONTEXT_PROMPT_TEMPLATE.format(
        known=_describe_known(known), message=message.strip()
    )
    raw = chat(prompt, system=SYSTEM_PROMPT)
    fresh = _validate(_extract_json(raw))
    area = _locate(message, fresh, known)

    merged = dict(known)
    for field in ("zone_name", "tank_level_percent", "days_since_delivery",
                  "locality", "ward", "candidate_zones"):
        merged.setdefault(field, None)

    for field in ("tank_level_percent", "days_since_delivery"):
        if fresh[field] is not None:
            merged[field] = fresh[field]

    # Zone, locality and ward move TOGETHER: a new area replaces all three,
    # so correcting "Vadapalani" to "Adyar" can't leave ward 130 behind.
    if area is not None:
        merged.update(area)

    # Not a fact about the zone -- it describes THIS message only, so it is
    # overwritten (not merged) every turn. Carrying it forward would make
    # the bot keep complaining about an area the volunteer has moved on from.
    merged["mentioned_place"] = fresh["mentioned_place"]
    return merged


def _pick_candidate(message: str, known: dict) -> dict | None:
    """A bare zone number chosen from the ambiguous-locality options."""
    pending = known.get("candidate_zones") or []
    bare = message.strip().lower().removeprefix("zone").strip(" .")
    if not (pending and bare.isdigit()):
        return None
    for key in pending:
        if ZONE_BY_KEY[key].zone_no == int(bare):
            return {"zone_name": key, "locality": known.get("locality"), "ward": None,
                    "candidate_zones": None}
    return None


def _locate(message: str, fresh: dict, known: dict) -> dict | None:
    """
    Work out which zone this message points at, if any. Returns the zone
    fields to set, or None when the message says nothing new about the area.

    Order of trust: an explicit ward/zone NUMBER (exact, from the Metrowater
    table); then the place name looked up in the boundary data; and only
    then the model's own zone_name, which it is told to give only when a
    zone itself is named. The model never maps a locality to a zone.
    """
    def area(zone, locality=None, ward=None):
        return {"zone_name": zone.key, "locality": locality, "ward": ward,
                "candidate_zones": None}

    pending = known.get("candidate_zones") or []
    numbered = zone_from_numbers(message)
    if numbered:
        return area(numbered.zone, ward=numbered.ward)

    place = fresh["mentioned_place"]
    if place:
        res = resolve_place(place)
        if res.kind in ("zone", "locality"):
            return area(res.zone, res.locality, res.ward)
        if res.kind == "ambiguous" and fresh["zone_name"] is None:
            return {"zone_name": None, "locality": res.locality, "ward": None,
                    "candidate_zones": [z.key for z in res.candidates]}

    if fresh["zone_name"] is not None:
        # If the volunteer is picking between ambiguous options, keep the
        # locality they already gave ("Gandhi Nagar" -> "the Kodambakkam one").
        locality = known.get("locality") if fresh["zone_name"] in pending else None
        return area(ZONE_BY_KEY[fresh["zone_name"]], locality)
    return None


AFFIRMATIVE = {
    "yes", "y", "yeah", "yep", "yes please", "correct", "right", "ok", "okay",
    "sure", "confirm", "confirmed", "true", "aam", "aama", "sari", "seri",
    "yes it is", "that's right", "thats right", "yes correct",
}
NEGATIVE = {
    "no", "n", "nope", "wrong", "incorrect", "not right", "nah", "illa",
    "no it isn't", "thats wrong", "that's wrong", "not correct",
}


def interpret_yes_no(message: str) -> bool | None:
    """
    Read a yes/no answer. Returns True, False, or None if it is neither.

    Deliberately a plain lookup rather than an LLM call: a confirmation is
    the point where the volunteer commits to facts that drive a real
    dispatch decision, so it must be predictable and must never be
    "interpreted" into the opposite of what was typed. Anything unclear
    returns None and the caller asks again.
    """
    text = message.strip().lower().strip(".!,")
    if text in AFFIRMATIVE:
        return True
    if text in NEGATIVE:
        return False
    # Allow a leading yes/no in a slightly longer reply ("yes, that's right").
    words = text.replace(",", " ").split()
    first = words[0] if words else ""
    if first in {"yes", "yeah", "yep", "correct", "right", "aama", "sari", "seri"}:
        return True
    if first in {"no", "nope", "wrong", "illa"}:
        return False
    return None
