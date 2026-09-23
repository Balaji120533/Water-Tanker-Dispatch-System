import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zone_registry import (
    ZONES, DIVISION_TO_ZONE, LOCALITIES, resolve_place, zone_from_numbers,
)


# --- the Metrowater table itself ----------------------------------------

def test_fifteen_zones_numbered_as_on_the_map():
    assert [z.zone_no for z in ZONES] == list(range(1, 16))


def test_every_division_1_to_200_belongs_to_exactly_one_zone():
    assert sorted(DIVISION_TO_ZONE) == list(range(1, 201))


def test_division_counts_match_the_printed_table():
    printed = {1: 14, 2: 7, 3: 12, 4: 15, 5: 15, 6: 15, 7: 15, 8: 15,
               9: 18, 10: 16, 11: 13, 12: 12, 13: 13, 14: 11, 15: 9}
    for z in ZONES:
        assert len(z.divisions) == printed[z.zone_no], z.name


def test_zone_14_has_its_split_division_range():
    # The one non-contiguous zone on the map: 168, 169, 183-191.
    assert DIVISION_TO_ZONE[168].name == "Perungudi"
    assert DIVISION_TO_ZONE[169].name == "Perungudi"
    assert DIVISION_TO_ZONE[170].name == "Adyar"
    assert DIVISION_TO_ZONE[183].name == "Perungudi"


def test_localities_were_loaded():
    assert len(LOCALITIES) > 400


# --- resolving what a volunteer typed ------------------------------------

def test_locality_resolves_to_its_zone_and_ward():
    r = resolve_place("vadapalani")
    assert r.kind == "locality"
    assert r.zone.key == "kodambakkam" and r.ward == 130


def test_zone_name_resolves_to_the_zone():
    r = resolve_place("Anna Nagar")
    assert r.kind == "zone" and r.zone.key == "anna_nagar"


def test_zone_name_beats_a_same_named_colony_elsewhere():
    # Zone 1 also contains a small "Anna Nagar" locality.
    assert resolve_place("anna nagar").zone.zone_no == 8


def test_spelling_variants_and_initials():
    assert resolve_place("T. Nagar").zone.key == "kodambakkam"
    assert resolve_place("KK Nagar").zone.key == "kodambakkam"
    assert resolve_place("K.K. Nagar").zone.key == "kodambakkam"
    assert resolve_place("sholinganallur").zone.key == "sozhanganallur"
    assert resolve_place("Tiruvottiyur").zone.key == "thiruvotriyur"


def test_small_typo_is_tolerated():
    assert resolve_place("vadapalni").zone.key == "kodambakkam"


def test_locality_in_several_zones_is_ambiguous_not_guessed():
    r = resolve_place("Gandhi Nagar")
    assert r.kind == "ambiguous"
    assert r.zone is None
    assert len(r.candidates) >= 2


def test_place_outside_the_corporation_is_unknown():
    for place in ["tambaram", "medavakkam", "", "   "]:
        assert resolve_place(place).kind == "unknown"


def test_ward_and_zone_numbers():
    assert zone_from_numbers("ward 130").zone.key == "kodambakkam"
    assert zone_from_numbers("division no 64").zone.key == "thiruvika_nagar"
    assert zone_from_numbers("zone 13").zone.key == "adyar"
    assert zone_from_numbers("Zone XIV").zone.key == "perungudi"


def test_out_of_range_numbers_are_rejected():
    assert zone_from_numbers("ward 250") is None
    assert zone_from_numbers("zone 16") is None
    assert zone_from_numbers("tank is 20 percent") is None
