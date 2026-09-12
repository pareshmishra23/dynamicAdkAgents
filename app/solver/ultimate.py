from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostItem:
    category: str
    detail: str
    usd: float
    inr: float


@dataclass(frozen=True)
class DiningPlace:
    name: str
    cuisine: str
    price: str
    distance: str


@dataclass(frozen=True)
class ItineraryStop:
    time: str
    place: str
    note: str


@dataclass(frozen=True)
class TripOption:
    label: str
    items: tuple[CostItem, ...]
    total_usd: float
    total_inr: float


@dataclass(frozen=True)
class UltimateChallengeSpec:
    id: str
    title: str
    origin: str
    destination_city: str
    nights: int
    date_window: str
    hotel: str
    office: str
    hotel_to_office_km: float
    preferred_airport: str
    requirements: tuple[str, ...]
    search_reasoning_note: str
    options: tuple[TripOption, ...]
    dining_near_hotel: tuple[DiningPlace, ...]
    touring_plan: tuple[ItineraryStop, ...]
    guidance_note: str
    needs_live_data: bool = True


def cost_item(category: str, detail: str, usd: float, inr: float) -> CostItem:
    return CostItem(category=category, detail=detail, usd=usd, inr=inr)


def total_of_items(items: tuple[CostItem, ...], currency: str) -> float:
    return round(sum(item.usd for item in items), 2) if currency == "usd" else round(sum(item.inr for item in items), 2)


ULTIMATE_CHALLENGE = UltimateChallengeSpec(
    id="ultimate-ny",
    title="The New York Trip Planner (Ultimate Challenge)",
    origin="Bengaluru (BLR)",
    destination_city="New York / Newark (EWR)",
    nights=7,
    date_window="October 3-7 (choose cheapest flight within window)",
    hotel="Extended Stay America Suites - Meadowlands (East Rutherford, NJ)",
    office="Flatiron Building, Manhattan (hotel ~10 km away)",
    hotel_to_office_km=10.0,
    preferred_airport="Newark (EWR) - much closer to hotel than JFK",
    requirements=(
        "1 week trip (7 nights) from Bengaluru to New York",
        "3 office days commuting by cab from hotel (Meadowlands) to Flatiron Building",
        "minimize taxi for Times Square (walkable / 1 subway stop from Flatiron)",
        "cheap dinner place near hotel",
        "2 touring days: good and cheap places nearby, include the place",
        "rent a car for 3 days (touring days), hotel and return fare",
        "flight date window early October 3-7, pick cheapest flight",
        "deliverable: cost matrix + 2 solution options",
    ),
    search_reasoning_note=(
        "Assumption: 7-night trip, flying into Newark (EWR) - much closer to the hotel "
        "than JFK - and using the rental car only for the 2 touring days (Manhattan "
        "parking is $40-60/day, so cabs/train are cheaper for the office run). "
        "Adjust if dates/duration differ."
    ),
    options=(
        TripOption(
            label="Option 1: Lean Budget",
            items=(
                cost_item("Flight (BLR<=>EWR, round trip, 1-stop)", "Air India via Delhi", 680.0, 58000.0),
                cost_item("Hotel - Ext. Stay America Meadowlands, 7 nights", "Standard studio @ ~$100/night", 700.0, 59500.0),
                cost_item("Office commute, 3 days (hotel<=>Flatiron, ~10 km)", "NJ Transit train, ~$20 round trip/day", 60.0, 5100.0),
                cost_item("Rental car, 3 days (touring days)", "Economy @ ~$40/day + tax", 130.0, 11000.0),
                cost_item("Dinner near hotel, 7 nights", "Diner/pizza, ~$14/night (cook a few in kitchenette)", 85.0, 7200.0),
                cost_item("2-day touring (transit + entries)", "Subway/PATH pass + free sights", 50.0, 4250.0),
            ),
            total_usd=1705.0,
            total_inr=145000.0,
        ),
        TripOption(
            label="Option 2: Better Value",
            items=(
                cost_item("Flight (BLR<=>EWR, round trip, 1-stop)", "Etihad/Emirates via Gulf hub, shorter layover", 950.0, 80750.0),
                cost_item("Hotel - Ext. Stay America Meadowlands, 7 nights", "Deluxe studio @ ~$130/night", 910.0, 77350.0),
                cost_item("Office commute, 3 days (hotel<=>Flatiron, ~10 km)", "Uber/Lyft, ~$110 round trip/day", 330.0, 28050.0),
                cost_item("Rental car, 3 days (touring days)", "Compact @ ~$55/day + tax", 180.0, 15300.0),
                cost_item("Dinner near hotel, 7 nights", "Casual sit-down, ~$25/night", 175.0, 14875.0),
                cost_item("2-day touring (transit + entries)", "Subway + one paid attraction + occasional Uber", 150.0, 12750.0),
            ),
            total_usd=2695.0,
            total_inr=229000.0,
        ),
    ),
    dining_near_hotel=(
        DiningPlace("Candlewyck Diner", "American diner", "$$", "~1 mi"),
        DiningPlace("Vesta Wood Fired", "Pizza/Italian", "$$", "~1.7 mi"),
        DiningPlace("Eros Cafe", "Pizza/Greek cafe", "$", "~1 mi"),
        DiningPlace("Samurai Sushi", "Japanese", "$$", "~1 mi"),
    ),
    touring_plan=(
        ItineraryStop("Morning", "Times Square", "Free to walk - 20 min from Flatiron Building"),
        ItineraryStop("Late morning", "Bryant Park & NY Public Library", "Free green space and free-to-enter library"),
        ItineraryStop("Midday", "High Line", "Free elevated park walk, Chelsea to Hudson Yards"),
        ItineraryStop("Lunch", "Chelsea Market", "Browse + cheap eats stalls"),
        ItineraryStop("Afternoon", "Madison Square Park / Flatiron District", "Free park right by your office building"),
        ItineraryStop("Evening", "Central Park", "Free - stroll or catch sunset"),
    ),
    guidance_note=(
        "Book flights ~6-9 weeks out for the best rate; confirm exact office days so "
        "the cab-vs-train choice lines up with rush-hour timing."
    ),
    needs_live_data=True,
)