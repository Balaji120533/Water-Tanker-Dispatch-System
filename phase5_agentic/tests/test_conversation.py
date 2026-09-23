import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conversation import (
    Session, COLLECTING, CONFIRMING, SUBMITTED, AWAITING_RECEIPT, CLOSED,
    describe_level, ask_for_missing, confirmation_question, receipt_question,
    unknown_area_reply, ambiguous_area_question, area_display,
)
from parsing import interpret_yes_no, VALID_ZONES


# --- session state -----------------------------------------------------

def test_new_session_starts_empty_and_collecting():
    s = Session()
    assert s.stage == COLLECTING
    assert not s.has_enough()
    assert set(s.missing_fields()) == {"zone_name", "tank_level_percent"}


def test_session_needs_both_zone_and_level():
    s = Session()
    s.facts["zone_name"] = "manali"
    assert not s.has_enough()
    assert s.missing_fields() == ["tank_level_percent"]

    s.facts["tank_level_percent"] = 10
    assert s.has_enough()


def test_days_since_delivery_is_optional():
    # A volunteer cannot be expected to know when the last tanker came;
    # entitlement can still be decided from the level alone.
    s = Session()
    s.facts.update({"zone_name": "manali", "tank_level_percent": 10})
    assert s.has_enough()


def test_reset_clears_facts_and_returns_to_collecting():
    s = Session()
    s.facts.update({"zone_name": "manali", "tank_level_percent": 10})
    s.stage = CONFIRMING
    s.reset_facts()
    assert s.stage == COLLECTING
    assert not s.has_enough()


def test_history_records_both_sides():
    s = Session()
    s.remember("user", "tank is empty")
    s.remember("assistant", "which area?")
    assert [h["role"] for h in s.history] == ["user", "assistant"]


def test_sessions_get_distinct_ids():
    assert Session().session_id != Session().session_id


# --- phrasing ----------------------------------------------------------

def test_describe_level_covers_the_range():
    assert describe_level(0) == "completely empty"
    assert describe_level(5) == "almost empty"
    assert describe_level(15) == "very low"
    assert describe_level(25) == "low"
    assert describe_level(50) == "about half full"
    assert describe_level(95) == "full"


def test_asks_for_area_when_only_level_is_known():
    q = ask_for_missing(["zone_name"], {"tank_level_percent": 5})
    assert "area" in q.lower()
    # It should acknowledge what it already heard rather than starting over.
    assert "almost empty" in q


def test_asks_for_level_when_only_area_is_known():
    q = ask_for_missing(["tank_level_percent"], {"zone_name": "manali"})
    assert "manali" in q.lower()
    assert "how much water" in q.lower()


def test_asks_for_both_when_nothing_is_known():
    q = ask_for_missing(["zone_name", "tank_level_percent"], {})
    assert "area" in q.lower() and "water" in q.lower()


def test_confirmation_reads_back_every_known_fact():
    q = confirmation_question(
        {"zone_name": "kodambakkam", "tank_level_percent": 5, "days_since_delivery": 3}
    )
    assert "Kodambakkam" in q
    assert "almost empty" in q and "5%" in q
    assert "3 days" in q
    assert q.rstrip().endswith("?")


def test_confirmation_omits_days_when_unknown():
    q = confirmation_question(
        {"zone_name": "manali", "tank_level_percent": 20, "days_since_delivery": None}
    )
    assert "day" not in q.lower()


def test_receipt_question_names_the_zone_and_asks_about_arrival():
    q = receipt_question("thiruvotriyur")
    # Named as printed on the Metrowater map, not by the internal key.
    assert "Zone 1 Thiruvottiyur" in q
    assert "?" in q


# --- areas we do not cover ---------------------------------------------

def test_every_metrowater_zone_is_reportable():
    # Previously only the 8 zones in today's schedule were accepted, so a
    # volunteer in Anna Nagar could not even report. Entitlement is the
    # engine's decision, not the parser's.
    assert len(VALID_ZONES) == 15
    assert "anna_nagar" in VALID_ZONES and "adyar" in VALID_ZONES


def test_unknown_area_says_so_and_offers_ways_to_answer():
    # Tambaram is outside the Corporation, so outside all 15 zones.
    reply = unknown_area_reply("tambaram", {"tank_level_percent": 15})
    assert "tambaram" in reply.lower()
    assert "ward" in reply.lower()
    # Lists every zone, numbered as on the Metrowater map.
    assert "10. Kodambakkam" in reply and "15. Shozhinganallur" in reply


def test_unknown_area_acknowledges_the_level_it_already_heard():
    reply = unknown_area_reply("tambaram", {"tank_level_percent": 15})
    assert "very low" in reply


def test_unknown_area_works_when_no_level_was_given():
    reply = unknown_area_reply("tambaram", {"tank_level_percent": None})
    assert "tank is" not in reply.lower()


def test_ambiguous_locality_lists_each_zone_and_asks():
    q = ambiguous_area_question("Gandhi Nagar", ["kodambakkam", "valasaravakkam"])
    assert "Zone 10 Kodambakkam" in q and "Zone 11 Valasaravakkam" in q
    assert "?" in q


def test_readback_shows_the_zone_a_locality_was_placed_in():
    # The locality->zone mapping decides where the tanker goes, so the
    # volunteer must see it before approving.
    facts = {"zone_name": "kodambakkam", "locality": "Vadapalani", "ward": 130}
    assert area_display(facts) == "Vadapalani, in Zone 10 Kodambakkam (ward 130)"


def test_readback_for_a_zone_named_directly():
    assert area_display({"zone_name": "anna_nagar"}) == "Zone 8 Anna Nagar"


# --- yes / no ----------------------------------------------------------

def test_plain_yes_and_no():
    assert interpret_yes_no("yes") is True
    assert interpret_yes_no("no") is False


def test_yes_no_inside_a_longer_reply():
    assert interpret_yes_no("yes, that's right") is True
    assert interpret_yes_no("no it's wrong") is False


def test_tamil_yes_no():
    assert interpret_yes_no("seri") is True
    assert interpret_yes_no("illa") is False


def test_ambiguous_answers_are_not_guessed():
    # A confirmation drives a real dispatch decision, so anything unclear
    # must come back as None and be asked again -- never assumed.
    for text in ["maybe", "i think so", "the tank is empty", ""]:
        assert interpret_yes_no(text) is None


def test_case_and_punctuation_are_ignored():
    assert interpret_yes_no("  YES!  ") is True
    assert interpret_yes_no("No.") is False
