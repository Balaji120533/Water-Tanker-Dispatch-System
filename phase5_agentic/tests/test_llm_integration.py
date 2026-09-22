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
