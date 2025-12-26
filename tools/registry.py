from tools.flight_tool import search_flights
from tools.food_tool import recommend_food
from tools.hotel_tool import search_hotels

TOOL_REGISTRY = {
    "search_flights": search_flights,
    "recommend_food": recommend_food,
    "search_hotels": search_hotels
}
