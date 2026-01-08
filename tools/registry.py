"""
Tool registry - now uses database-backed tools instead of hardcoded data.
"""

from tools.db_tools import search_flights, search_hotels, recommend_food

TOOL_REGISTRY = {
    "search_flights": search_flights,
    "recommend_food": recommend_food,
    "search_hotels": search_hotels
}