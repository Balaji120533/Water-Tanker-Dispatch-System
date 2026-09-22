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
    assert result == {"zone_name": "manali", "tank_level_percent": 15, "days_since_delivery": 3}


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
