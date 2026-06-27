import json
import json
from pathlib import Path

# Load mock data once
_data_path = Path(__file__).parent / "data" / "mock_data.json"
with open(_data_path) as f:
    MOCK_DATA = json.load(f)


# --- Safety: input validator ---
def _validate_budget(budget, name: str = "budget") -> float:
    if isinstance(budget, str):
        try:
            budget = float(budget)
        except ValueError:
            raise ValueError(f"{name} could not be converted to a number: {repr(budget)}")
    if not isinstance(budget, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(budget).__name__}")
    if budget <= 0:
        raise ValueError(f"{name} must be positive, got {budget}")
    if budget > 100_000:
        raise ValueError(f"{name} is unrealistically large: {budget}")
    return float(budget)

def _validate_nights(nights) -> int:
    # Auto-cast string to int (small models often send "3" instead of 3)
    if isinstance(nights, str):
        try:
            nights = int(nights)
        except ValueError:
            raise ValueError(f"nights could not be converted to integer: {repr(nights)}")
    if not isinstance(nights, int):
        raise ValueError(f"nights must be an integer, got {type(nights).__name__}")
    if nights <= 0 or nights > 30:
        raise ValueError(f"nights must be between 1 and 30, got {nights}")
    return nights

def _sanitize_string(value: str, name: str = "field") -> str:
    """Strip prompt-injection attempts from string inputs."""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    sanitized = value.strip()
    if len(sanitized) > 100:
        raise ValueError(f"{name} is too long (max 100 chars)")
    return sanitized


# --- Tool 1: search_flights ---
def search_flights(destination: str, budget_eur: float) -> dict:
    """
    Search for available flights to a destination within a budget.

    Args:
        destination: Target city (e.g. 'Porto')
        budget_eur: Maximum price in EUR per person

    Returns:
        dict with matching flights or error
    """
    try:
        destination = _sanitize_string(destination, "destination")
        budget_eur = _validate_budget(budget_eur, "budget_eur")
    except ValueError as e:
        return {"error": str(e)}

    matches = [
        f for f in MOCK_DATA["flights"]
        if f["destination"].lower() == destination.lower()
        and f["price_eur"] <= budget_eur
    ]

    if not matches:
        return {"error": f"No flights found to {destination} under €{budget_eur}"}

    # Return cheapest option
    best = min(matches, key=lambda f: f["price_eur"])
    return {
        "flight_id": best["id"],
        "airline": best["airline"],
        "price_eur": best["price_eur"],
        "duration_hours": best["duration_hours"],
        "destination": best["destination"]
    }


# --- Tool 2: search_hotels ---
def search_hotels(city: str, nights: int, budget_per_night_eur: float) -> dict:
    """
    Search for hotels in a city within a nightly budget.

    Args:
        city: City name (e.g. 'Porto')
        nights: Number of nights to stay
        budget_per_night_eur: Max price per night in EUR

    Returns:
        dict with best hotel match and total cost, or error
    """
    try:
        city = _sanitize_string(city, "city")
        nights = _validate_nights(nights)
        budget_per_night_eur = _validate_budget(budget_per_night_eur, "budget_per_night_eur")
    except ValueError as e:
        return {"error": str(e)}

    matches = [
        h for h in MOCK_DATA["hotels"]
        if h["city"].lower() == city.lower()
        and h["price_per_night_eur"] <= budget_per_night_eur
    ]

    if not matches:
        return {"error": f"No hotels found in {city} under €{budget_per_night_eur}/night"}

    # Return best value (highest stars within budget)
    best = max(matches, key=lambda h: h["stars"])
    total = best["price_per_night_eur"] * nights
    return {
        "hotel_id": best["id"],
        "name": best["name"],
        "stars": best["stars"],
        "price_per_night_eur": best["price_per_night_eur"],
        "nights": nights,
        "total_hotel_cost_eur": total,
        "amenities": best["amenities"]
    }


# --- Tool 3: calculate ---
def calculate(items) -> dict:
    """
    Sum a list of costs and return the total.

    Args:
        items: List of numeric values (EUR amounts). Also accepts a JSON string like "[155, 330]".

    Returns:
        dict with total, or error
    """
    # Auto-parse if model passes a string instead of a list
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except (json.JSONDecodeError, ValueError):
            return {"error": f"Could not parse items string as a list: {repr(items)}"}

    if not isinstance(items, list):
        return {"error": f"items must be a list, got {type(items).__name__}"}
    if len(items) == 0:
        return {"error": "items list is empty"}
    if len(items) > 50:
        return {"error": "Too many items (max 50)"}

    validated = []
    for i, val in enumerate(items):
        if not isinstance(val, (int, float)):
            return {"error": f"Item at index {i} is not a number: {repr(val)}"}
        if val < 0:
            return {"error": f"Item at index {i} is negative: {val}"}
        validated.append(float(val))

    total = round(sum(validated), 2)
    return {
        "items": validated,
        "total_eur": total
    }