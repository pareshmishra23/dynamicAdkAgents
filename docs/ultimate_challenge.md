# The Ultimate Challenge — Single Page

> **Challenge:** Plan a 1-week (7-night) Bangalore → New York trip. Be the agent pool's final, live-data proof point — solved only after all beads ship, using Registry-granted web tools (search/fetch). This page is the single-page spec; the machine-readable golden reference lives in `app/solver/ultimate.py` (tests pin it).

## 1. The ask (verbatim + normalized)

"Going to USA. New York for 1 week. 3 days I need to go to office by cab. Taxi minimal for Times Square. Hotel is 10 km away — Extended Stay America Suites, Meadowlands — to Flatiron Building. Need a cheap dinner place nearby. Next 2 days tour good and cheap places I can enjoy. Include rental car for 3 days, hotel, and return fare. Dates: 3–7 October, choose cheapest flight. **Provide cost matrix + 2 solution options.**"

## 2. Fixed constraints

| Constraint | Value |
|---|---|
| Trip length | 7 nights |
| Origin | Bengaluru (BLR) |
| Preferred airport | **Newark (EWR)** — close to hotel; not JFK |
| Hotel | Extended Stay America Suites–Meadowlands, East Rutherford, NJ |
| Office | Flatiron Building, Manhattan (hotel ≈ **10 km** away) |
| Office commute | 3 days by cab / transit, hotel↔Flatiron |
| Times Square | Walkable (~20 min) or 1 subway stop from Flatiron — no extra taxi |
| Touring | 2 days, cheap + enjoyable, one listed place per stop |
| Rental car | 3 days (touring days only; Manhattan parking $40–60/day) |
| Dates | Early October 3–7; pick cheapest flight |
| Deliverable | Cost matrix + **2 options** (Lean Budget / Better Value) |

## 3. Search reasoning (the "proof" the pool must reproduce)

- EWR over JFK (closer to hotel).
- Rental car only for the 2 touring days; cabs/train cheaper for the 3 office days.
- Times Square needs **no cab** (walkable from Flatiron).
- Book ~6–9 weeks out; confirm exact office days for rush-hour cab-vs-train timing.

## 4. Golden reference — cost matrix (per person, ~₹85/USD)

| Item | Option 1: Lean Budget | Option 2: Better Value |
|---|---|---|
| Flight (BLR⇄EWR, 1-stop) | Air India via Delhi — $680 / ₹58,000 | Etihad/Emirates via Gulf hub — $950 / ₹80,750 |
| Hotel, 7 nights | Standard @ $100/night — $700 / ₹59,500 | Deluxe @ $130/night — $910 / ₹77,350 |
| Office commute, 3 days | NJ Transit ~$20/day — $60 / ₹5,100 | Uber/Lyft ~$110/day — $330 / ₹28,050 |
| Rental car, 3 days | Economy ~$40/day — $130 / ₹11,000 | Compact ~$55/day — $180 / ₹15,300 |
| Dinner, 7 nights | Diner/pizza ~$14/night — $85 / ₹7,200 | Sit-down ~$25/night — $175 / ₹14,875 |
| 2-day touring | Subway/PATH + free sights — $50 / ₹4,250 | Subway + 1 paid + Uber — $150 / ₹12,750 |
| **Total** | **≈ $1,705 / ₹1,45,000** | **≈ $2,695 / ₹2,29,000** |

## 5. Golden reference — cheap dinner near hotel

| Place | Cuisine | Price | Distance |
|---|---|---|---|
| Candlewyck Diner | American diner | $$ | ~1 mi |
| Vesta Wood Fired | Pizza/Italian | $$ | ~1.7 mi |
| Eros Cafe | Pizza/Greek | $ | ~1 mi |
| Samurai Sushi | Japanese | $$ | ~1 mi |

## 6. Golden reference — 2 cheap touring days

| When | Place | Why it's free/cheap |
|---|---|---|
| Morning | Times Square | Free, 20 min from Flatiron |
| Late morning | Bryant Park & NY Public Library | Free / free entrance |
| Midday | High Line | Free elevated park |
| Lunch | Chelsea Market | Cheap food stalls |
| Afternoon | Madison Square Park / Flatiron | Free park by office |
| Evening | Central Park | Free, sunset |

## 7. Pass criteria (when the pool finally solves it live)

- Matrix matches or beats the golden reference with **live-sourced prices + sources**.
- Exactly 2 options, both complete to the total (no missing rows).
- Every requirement in §2 is addressed explicitly (3 cab office days, Times Square without taxi, cheap dinner, 2 touring days, 3-day rental + return fare, dates).
- Cost columns add up: Option 1 = $1,705 (± tolerance), Option 2 = $2,695.
- Uses web tools granted by the Registry (MCP/search boundary from BEADs 7+).

## 8. Status

- [x] Spec captured (this page)
- [x] Golden reference encoded + pinned by tests (`app/solver/ultimate.py`, `tests/unit/test_ultimate_challenge.py`)
- [ ] Solved live by the pool (post-BEAD 9, needs web access)