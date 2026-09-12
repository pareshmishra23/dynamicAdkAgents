from __future__ import annotations

from app.solver.ultimate import (
    ULTIMATE_CHALLENGE,
    DiningPlace,
    TripOption,
    cost_item,
    total_of_items,
)


def test_challenge_describes_trip_envelope() -> None:
    spec = ULTIMATE_CHALLENGE
    assert spec.id == "ultimate-ny"
    assert spec.origin == "Bengaluru (BLR)"
    assert "Newark" in spec.destination_city
    assert spec.nights == 7
    assert spec.date_window.startswith("October")
    assert spec.hotel_to_office_km == 10.0
    assert spec.needs_live_data


def test_requirements_cover_the_ask() -> None:
    text = " ".join(ULTIMATE_CHALLENGE.requirements).lower()
    assert "7 nights" in text
    assert "3 office days" in text
    assert "cab" in text
    assert "cheap dinner" in text
    assert "2 touring days" in text
    assert "rent a car for 3 days" in text
    assert "cost matrix" in text
    assert "2 solution options" in text


def test_two_options_exist_and_are_complete() -> None:
    spec = ULTIMATE_CHALLENGE
    assert len(spec.options) == 2
    for option in spec.options:
        assert len(option.items) == 6
        assert all(item.detail for item in option.items)
        assert option.label


def test_option_totals_match_the_golden_reference() -> None:
    options = {o.label: o for o in ULTIMATE_CHALLENGE.options}
    lean = options["Option 1: Lean Budget"]
    better = options["Option 2: Better Value"]
    assert lean.total_usd == 1705.0
    assert lean.total_inr == 145000.0
    assert better.total_usd == 2695.0
    assert better.total_inr == 229000.0


def test_option_item_sum_equals_declared_total() -> None:
    for option in ULTIMATE_CHALLENGE.options:
        assert total_of_items(option.items, "usd") == option.total_usd
        assert abs(total_of_items(option.items, "inr") - option.total_inr) <= 100


def test_lean_budget_picks_cheapest_each_category() -> None:
    lean = {i.category: i for i in ULTIMATE_CHALLENGE.options[0].items}
    assert "Air India" in lean["Flight (BLR<=>EWR, round trip, 1-stop)"].detail
    assert "$100" in lean["Hotel - Ext. Stay America Meadowlands, 7 nights"].detail
    assert "NJ Transit" in lean["Office commute, 3 days (hotel<=>Flatiron, ~10 km)"].detail
    assert "Economy" in lean["Rental car, 3 days (touring days)"].detail
    assert "Subway/PATH" in lean["2-day touring (transit + entries)"].detail


def test_better_value_prefers_short_connections() -> None:
    better = {i.category: i for i in ULTIMATE_CHALLENGE.options[1].items}
    assert "shorter layover" in better["Flight (BLR<=>EWR, round trip, 1-stop)"].detail


def test_dinner_spots_are_result_near_hotel() -> None:
    spec = ULTIMATE_CHALLENGE
    assert len(spec.dining_near_hotel) == 4
    assert "East Rutherford" in spec.hotel or spec.preferred_airport.startswith("Newark")
    prices = {p.name: p.price for p in spec.dining_near_hotel}
    assert prices["Eros Cafe"] == "$"
    assert all(p.price in ("$", "$$") for p in spec.dining_near_hotel)


def test_touring_plan_is_free_or_cheap() -> None:
    spec = ULTIMATE_CHALLENGE
    assert len(spec.touring_plan) == 6
    for stop in spec.touring_plan:
        assert "free" in stop.note.lower() or "cheap" in stop.note.lower()
    assert spec.touring_plan[0].place == "Times Square"
    assert spec.touring_plan[-1].place == "Central Park"


def test_search_reasoning_reflects_scenario_insights() -> None:
    note = ULTIMATE_CHALLENGE.search_reasoning_note.lower()
    assert "ewr" in note
    assert "parking" in note
    assert "edger" not in note


def test_cost_item_helper_builds_valid_row() -> None:
    item = cost_item("X", "detail", 10.0, 850.0)
    assert item.usd == 10.0
    assert item.inr == 850.0
    assert total_of_items((item,), "inr") == 850.0