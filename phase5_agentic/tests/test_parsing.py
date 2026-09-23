import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from parsing import _extract_json, _validate, ParseError, VALID_ZONES


def test_extract_json_from_clean_output():
    data = _extract_json('{"zone_name": "manali", "tank_level_percent": 10, "days_since_delivery": 2}')
    assert data["zone_name"] == "manali"


def test_extract_json_strips_surrounding_text():
    data = _extract_json('Here is the JSON:\n{"zone_name": "adyar", "tank_level_percent": null, "days_since_delivery": null}\nHope this helps.')
    assert data["zone_name"] == "adyar"


def test_extract_json_raises_on_no_json():
    with pytest.raises(ParseError):
        _extract_json("I cannot determine the zone from this message.")


def test_extract_json_raises_on_malformed_json():
    with pytest.raises(ParseError):
        _extract_json('{"zone_name": "manali", oops}')


def test_validate_accepts_well_formed_data():
    result = _validate({"zone_name": "manali", "tank_level_percent": 15, "days_since_delivery": 3})
    assert result == {"zone_name": "manali", "tank_level_percent": 15,
                      "days_since_delivery": 3, "mentioned_place": None}


def test_mentioned_place_is_length_capped():
    # Free text from the model that gets echoed into the chat, so a
    # runaway response must not become a wall of text in the UI.
    result = _validate({"zone_name": None, "tank_level_percent": None,
                        "days_since_delivery": None, "mentioned_place": "x" * 500})
    assert len(result["mentioned_place"]) <= 40


def test_blank_mentioned_place_becomes_none():
    result = _validate({"zone_name": None, "tank_level_percent": None,
                        "days_since_delivery": None, "mentioned_place": "   "})
    assert result["mentioned_place"] is None


def test_mentioned_place_never_substitutes_for_a_zone():
    # The whole point of the split: naming a place we do not serve must
    # not become coverage for it.
    result = _validate({"zone_name": None, "tank_level_percent": 10,
                        "days_since_delivery": None, "mentioned_place": "vadapalani"})
    assert result["zone_name"] is None


def test_validate_accepts_nulls_for_missing_info():
    result = _validate({"zone_name": "manali", "tank_level_percent": None, "days_since_delivery": None})
    assert result["tank_level_percent"] is None


def test_validate_rejects_unknown_zone():
    with pytest.raises(ParseError):
        _validate({"zone_name": "mumbai", "tank_level_percent": 10, "days_since_delivery": 1})


def test_validate_rejects_out_of_range_level():
    with pytest.raises(ParseError):
        _validate({"zone_name": "manali", "tank_level_percent": 150, "days_since_delivery": 1})


def test_validate_rejects_negative_level():
    with pytest.raises(ParseError):
        _validate({"zone_name": "manali", "tank_level_percent": -5, "days_since_delivery": 1})


def test_validate_rejects_negative_days():
    with pytest.raises(ParseError):
        _validate({"zone_name": "manali", "tank_level_percent": 10, "days_since_delivery": -1})


def test_validate_rejects_non_dict():
    with pytest.raises(ParseError):
        _validate(["not", "a", "dict"])


def test_validate_rejects_wrong_type_for_level():
    with pytest.raises(ParseError):
        _validate({"zone_name": "manali", "tank_level_percent": "very low", "days_since_delivery": 1})


def test_all_valid_zones_pass_validation():
    for zone in VALID_ZONES:
        result = _validate({"zone_name": zone, "tank_level_percent": 20, "days_since_delivery": 1})
        assert result["zone_name"] == zone


def test_zone_choice_keeps_the_level_already_given():
    # Answering "which Gandhi Nagar?" with "10" once also overwrote the
    # tank level with 10%. A bare zone number must be taken as a zone
    # choice only -- and settled without the model.
    from parsing import parse_in_context
    known = {"zone_name": None, "tank_level_percent": 0, "days_since_delivery": None,
             "locality": "Gandhi Nagar", "ward": None,
             "candidate_zones": ["kodambakkam", "valasaravakkam"]}
    result = parse_in_context("10", known)
    assert result["zone_name"] == "kodambakkam"
    assert result["tank_level_percent"] == 0
    assert result["locality"] == "Gandhi Nagar"
    assert result["candidate_zones"] is None
