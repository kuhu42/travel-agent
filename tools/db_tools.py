"""
Database-backed tools that execute MongoDB queries.
These tools no longer contain hardcoded data - they query the database.
"""

from pymongo import MongoClient
from tools.query_generator import generate_query
from langfuse_config import create_span

client = MongoClient("mongodb://localhost:27017")
db = client["travel_agent"]


def search_flights(destination, dates, source=None, budget=None, filters=None):
    """
    Search flights using MongoDB query generation.
    """
    with create_span("search_flights_db", input={
        "destination": destination,
        "dates": dates,
        "source": source,
        "budget": budget,
        "filters": filters
    }) as span:
        
        print(f"\n[DB TOOL] search_flights called")
        print(f"[DB TOOL] Params: dest={destination}, source={source}, budget={budget}")
        
        # Build intent
        intent = {
            "tool": "search_flights",
            "args": {
                "destination": destination,
                "source": source,
                "dates": dates,
                "budget": budget,
                "filters": filters or {}
            }
        }
        
        # Generate MongoDB query
        query_spec = generate_query(intent, {})
        
        if not query_spec:
            print("[DB TOOL] Failed to generate query")
            return []
        
        # Execute query
        collection = db[query_spec["collection"]]
        query = query_spec["query"]
        sort = list(query_spec.get("sort", {}).items())
        limit = query_spec.get("limit", 10)
        
        print(f"[DB TOOL] Executing query: {query}")
        print(f"[DB TOOL] Sort: {sort}, Limit: {limit}")
        
        results = list(collection.find(query).sort(sort).limit(limit))
        
        # Remove MongoDB _id field
        for result in results:
            result.pop("_id", None)
        
        print(f"[DB TOOL] Found {len(results)} flights")
        
        span.update(output={"count": len(results)}, metadata={"query": query})
        
        return results


def search_hotels(destination, budget=None, dates=None):
    """
    Search hotels using MongoDB query generation.
    """
    with create_span("search_hotels_db", input={
        "destination": destination,
        "budget": budget,
        "dates": dates
    }) as span:
        
        print(f"\n[DB TOOL] search_hotels called")
        print(f"[DB TOOL] City: {destination}, Budget: {budget}")
        
        intent = {
            "tool": "search_hotels",
            "args": {
                "destination": destination,
                "budget": budget,
                "dates": dates
            }
        }
        
        query_spec = generate_query(intent, {})
        
        if not query_spec:
            return []
        
        collection = db[query_spec["collection"]]
        query = query_spec["query"]
        sort = list(query_spec.get("sort", {}).items())
        limit = query_spec.get("limit", 10)
        
        print(f"[DB TOOL] Query: {query}")
        
        results = list(collection.find(query).sort(sort).limit(limit))
        
        for result in results:
            result.pop("_id", None)
        
        print(f"[DB TOOL] Found {len(results)} hotels")
        
        span.update(output={"count": len(results)})
        
        return results


def recommend_food(destination, preference=None):
    """
    Recommend restaurants using MongoDB query generation.
    """
    with create_span("recommend_food_db", input={
        "destination": destination,
        "preference": preference
    }) as span:
        
        print(f"\n[DB TOOL] recommend_food called")
        print(f"[DB TOOL] City: {destination}, Preference: {preference}")
        
        intent = {
            "tool": "recommend_food",
            "args": {
                "destination": destination,
                "preference": preference
            }
        }
        
        query_spec = generate_query(intent, {})
        
        if not query_spec:
            return []
        
        collection = db[query_spec["collection"]]
        query = query_spec["query"]
        sort = list(query_spec.get("sort", {}).items())
        limit = query_spec.get("limit", 10)
        
        print(f"[DB TOOL] Query: {query}")
        
        results = list(collection.find(query).sort(sort).limit(limit))
        
        for result in results:
            result.pop("_id", None)
        
        print(f"[DB TOOL] Found {len(results)} restaurants")
        
        span.update(output={"count": len(results)})
        
        return results