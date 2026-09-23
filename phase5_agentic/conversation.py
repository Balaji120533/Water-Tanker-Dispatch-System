"""
Conversation state for the volunteer chat.

A volunteer reports water trouble the way people actually talk -- a bit at
a time, out of order, and sometimes correcting themselves. This module
tracks one such conversation from the first message through to the
volunteer confirming that water actually arrived.

RULE 2 still holds throughout: this module decides what to ASK, never what
is true. Entitlement remains the logic engine's call, allocation the CSP
solver's. The only judgements made here are conversational ones -- is
enough known to proceed, has the volunteer confirmed, has the delivery
been acknowledged.

Pure module: no HTTP, no LLM calls. The backend supplies parsed facts and
engine decisions; this decides what happens next in the dialogue.
"""

from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field

from zone_registry import ZONE_BY_KEY, zone_list_text

# Conversation stages, in the order a report moves through them.
COLLECTING = "collecting"      # still gathering zone / level
CONFIRMING = "confirming"      # facts read back, awaiting yes/no
SUBMITTED = "submitted"        # decision made, awaiting or holding a slot
AWAITING_RECEIPT = "awaiting_receipt"  # driver marked delivered, asking the volunteer
CLOSED = "closed"              # volunteer confirmed water arrived (or wasn't entitled)

REQUIRED_FIELDS = ("zone_name", "tank_level_percent")


def empty_facts() -> dict:
    return {
        "zone_name": None, "tank_level_percent": None, "days_since_delivery": None,
        # Where in the zone, when the volunteer named a locality or ward --
        # read back so they can check the zone it was placed in.
        "locality": None, "ward": None,
        # Set while a locality name is ambiguous across zones.
        "candidate_zones": None,
        # Not a fact -- the place name as typed, used only to tell an
        # uncovered area apart from no area at all when asking again.
        "mentioned_place": None,
    }


@dataclass
class Session:
    """One volunteer's conversation. Lives until the delivery is settled."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    stage: str = COLLECTING
    facts: dict = field(default_factory=empty_facts)
    # Set once the engine has ruled and (if entitled) a slot is known.
    decision: dict | None = None
    delivery_confirmed: bool | None = None
    created_at: float = field(default_factory=time.time)
    history: list = field(default_factory=list)

    def remember(self, role: str, text: str) -> None:
        self.history.append({"role": role, "text": text, "at": time.time()})

    def missing_fields(self) -> list[str]:
        return [f for f in REQUIRED_FIELDS if self.facts.get(f) is None]

    def has_enough(self) -> bool:
        return not self.missing_fields()

    def reset_facts(self) -> None:
        """Used when the volunteer says the read-back was wrong."""
        self.facts = empty_facts()
        self.stage = COLLECTING


# --- phrasing helpers --------------------------------------------------
# Kept here rather than in the frontend so the wording is testable and the
# UI stays a dumb renderer.

def describe_level(percent: int) -> str:
    if percent <= 2:
        return "completely empty"
    if percent <= 10:
        return "almost empty"
    if percent <= 20:
        return "very low"
    if percent <= 35:
        return "low"
    if percent <= 60:
        return "about half full"
    if percent <= 85:
        return "fairly full"
    return "full"


def zone_display(key: str) -> str:
    """A zone key as the volunteer should see it: "Zone 10 Kodambakkam"."""
    zone = ZONE_BY_KEY.get(key)
    return zone.label() if zone else key.replace("_", " ").title()


def area_display(facts: dict) -> str:
    """
    The area read back to the volunteer. When they named a locality, show
    the zone it was placed in too -- that mapping decides where the tanker
    goes, so it is exactly what they should get the chance to correct.
    """
    zone = zone_display(facts["zone_name"])
    suffix = f" (ward {facts['ward']})" if facts.get("ward") else ""
    locality = facts.get("locality")
    if locality:
        return f"{locality}, in {zone}{suffix}"
    return f"{zone}{suffix}"


def unknown_area_reply(place: str, facts: dict) -> str:
    """
    The volunteer named a place that is not inside any of the 15 zones.

    Worth its own message: without it the bot just re-asks "which area?"
    and the volunteer retypes the same name forever, unable to tell whether
    they were misheard or simply are not covered. Saying so plainly, and
    offering ways to answer that WILL work, ends the loop either way.
    """
    level = facts.get("tank_level_percent")
    heard = f"I heard the tank is {describe_level(level)}, but " if level is not None else ""
    return (f"{heard}I couldn't find “{place}” inside Chennai Metrowater's 15 zones. It may "
            "be outside the Corporation limits, or spelled differently.\n\n"
            "You can tell me a well-known area nearby, your ward (division) number, or "
            f"your zone:\n{zone_list_text()}")


def ambiguous_area_question(locality: str, candidates: list[str]) -> str:
    """The same locality name exists in several zones -- ask, never guess."""
    options = "\n".join(f"• {zone_display(k)}" for k in candidates)
    return (f"There is a “{locality}” in more than one zone:\n{options}\n\n"
            "Which one is yours? You can reply with the zone name or number, or your "
            "ward number.")


def ask_for_missing(missing: list[str], facts: dict) -> str:
    """The follow-up question, phrased around what is already known."""
    if "zone_name" in missing and "tank_level_percent" in missing:
        return ("Which area are you reporting for, and roughly how much water is left "
                "in the tank?")

    if "zone_name" in missing:
        level = facts.get("tank_level_percent")
        if level is not None:
            return (f"Got it — the tank is {describe_level(level)}. "
                    "Which area is this? (for example Vadapalani, Anna Nagar, or your ward number)")
        return "Which area are you reporting for?"

    # only the level is missing
    return (f"Thanks — noted for {area_display(facts)}. Roughly how much water is left in "
            "the tank? You can just say “almost empty”, “half”, or “still quite full”.")


def confirmation_question(facts: dict) -> str:
    """Read the facts back before anything is decided on them."""
    level = facts["tank_level_percent"]
    line = (f"Let me make sure I have this right:\n\n"
            f"• Area: {area_display(facts)}\n"
            f"• Tank: {describe_level(level)} (about {level}%)")
    days = facts.get("days_since_delivery")
    if days is not None:
        line += f"\n• Last delivery: {days} day{'s' if days != 1 else ''} ago"
    return line + "\n\nIs that correct?"


def receipt_question(zone: str) -> str:
    return (f"The driver has marked the delivery to {zone_display(zone)} as "
            "complete. Did the tanker actually arrive and fill your tank?")
