"""
Live integration tests that actually call the Groq API. Skipped
automatically if no real GROQ_API_KEY is configured, so the rest of the
test suite (and CI, and a reviewer without a key) never hard-fails on
these -- only the pure validation logic in test_parsing.py is required to
pass unconditionally.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from dotenv import load_dotenv

load_dotenv()

_has_key = bool(os.environ.get("GROQ_API_KEY")) and os.environ.get("GROQ_API_KEY") != "your_groq_api_key_here"

pytestmark = pytest.mark.skipif(not _has_key, reason="GROQ_API_KEY not configured")


def test_parse_message_extracts_zone_and_level():
    from parsing import parse_message
    result = parse_message("The tank in Manali is almost completely empty, maybe 5%.")
    assert result["zone_name"] == "manali"
    assert result["tank_level_percent"] is not None
    assert result["tank_level_percent"] < 20


def test_parse_message_returns_null_for_unmentioned_days():
    from parsing import parse_message
    result = parse_message("Manali's tank is very low.")
    assert result["zone_name"] == "manali"
    # days_since_delivery wasn't mentioned -- must be null, not guessed
    assert result["days_since_delivery"] is None


def test_context_parsing_accumulates_facts_across_turns():
    # The exact sequence that failed before sessions existed: the first
    # message carries the area, the second carries the level. Parsed in
    # isolation neither turn has enough to decide on.
    from parsing import parse_in_context
    empty = {"zone_name": None, "tank_level_percent": None, "days_since_delivery": None}

    after_first = parse_in_context("the tank in kodambakkam is getting less", empty)
    assert after_first["zone_name"] == "kodambakkam"

    after_second = parse_in_context("tank is almost empty", after_first)
    assert after_second["zone_name"] == "kodambakkam"          # kept
    assert after_second["tank_level_percent"] is not None       # gained
    assert after_second["tank_level_percent"] < 15              # "almost empty"


def test_descriptive_phrases_yield_a_level_not_null():
    # "getting less" previously returned null, so the bot asked for the
    # level again even though the volunteer had just described it.
    from parsing import parse_in_context
    empty = {"zone_name": None, "tank_level_percent": None, "days_since_delivery": None}
    result = parse_in_context("water in manali is getting less", empty)
    assert result["tank_level_percent"] is not None


def test_locality_is_placed_in_its_zone_by_the_lookup_table():
    # The exact message from the screenshot that looped on "which area?".
    from parsing import parse_in_context
    empty = {"zone_name": None, "tank_level_percent": None, "days_since_delivery": None}
    result = parse_in_context("the tank is very less at vadapalani", empty)
    assert result["zone_name"] == "kodambakkam"
    assert result["locality"] == "Vadapalani"
    assert result["ward"] == 130


def test_zone_that_was_not_in_todays_schedule_is_now_reportable():
    from parsing import parse_in_context
    empty = {"zone_name": None, "tank_level_percent": None, "days_since_delivery": None}
    result = parse_in_context("the tank in anna nagar is almost empty", empty)
    assert result["zone_name"] == "anna_nagar"


def test_place_outside_the_zones_is_reported_not_silently_dropped():
    # Tambaram is outside the Corporation. The zone must stay null (never
    # invent coverage); mentioned_place records what was typed so the bot
    # can say WHY it cannot help.
    from parsing import parse_in_context
    empty = {"zone_name": None, "tank_level_percent": None, "days_since_delivery": None}
    result = parse_in_context("no water at all in tambaram", empty)
    assert result["zone_name"] is None
    assert "tambaram" in (result["mentioned_place"] or "").lower()


def test_mentioned_place_does_not_persist_across_turns():
    # It describes one message only. If it stuck, the bot would keep
    # complaining about an area the volunteer already moved on from.
    from parsing import parse_in_context
    empty = {"zone_name": None, "tank_level_percent": None, "days_since_delivery": None}
    first = parse_in_context("water is very less at tambaram", empty)
    assert first["mentioned_place"] is not None

    second = parse_in_context("actually the tank is almost empty", first)
    assert second["mentioned_place"] is None


def test_explain_decision_preserves_conclusion():
    from explain import explain_decision
    trace = (
        "entitled(manali)   [entitled(Zone) :- tank_level(Zone, Level), lt30(Level).]\n"
        "  tank_level(manali, 15)   [fact in KB]\n"
        "  lt30(15)   [builtin arithmetic check]"
    )
    result = explain_decision("manali", entitled=True, high_priority=False, proof_trace=trace)
    assert "manali" in result.lower()
    assert len(result) > 0
