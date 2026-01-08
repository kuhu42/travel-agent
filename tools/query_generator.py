"""
Query Generator: Uses LLM to convert natural language to MongoDB queries.
Follows the flow: Intent Analysis → Query Planning → Query Execution
"""

import json
from llm.ollama_client import call_ollama
from langfuse_config import create_span

# Database schemas (agent only knows structure, not data)
DATABASE_SCHEMA = """
FLIGHTS COLLECTION:
{
  "index": int,
  "airline": string (Indigo, Vistara, Air India, SpiceJet, GoAir, AirAsia),
  "flight": string (flight code like "IN123"),
  "source_city": string (Mumbai, Delhi, Bangalore, etc.),
  "departure_time": string (HH:MM format),
  "stops": int (0, 1, 2),
  "arrival_time": string (HH:MM format),
  "destination_city": string,
  "class": string (Economy, Business),
  "duration": string (e.g., "2h 30m"),
  "days_left": int (days until departure),
  "price": int (in rupees)
}

HOTELS COLLECTION:
{
  "index": int,
  "name": string,
  "city": string,
  "price_per_night": int (in rupees),
  "rating": float (1.0-5.0),
  "amenities": array of strings (WiFi, Breakfast, Pool, Gym, Spa, Restaurant)
}

RESTAURANTS COLLECTION:
{
  "index": int,
  "name": string,
  "city": string,
  "cuisine": string (French, Italian, Chinese, etc.),
  "price_range": string ($, $$, $$$, $$$$),
  "rating": float (1.0-5.0),
  "vegetarian": boolean,
  "fine_dining": boolean
}
"""


def generate_query(intent: dict, context: dict) -> dict:
    """
    Generate MongoDB query based on intent and context.
    
    Args:
        intent: Parsed intent with tool, filters, etc.
        context: Conversation context (source, destination, dates, etc.)
    
    Returns:
        dict with collection, query, sort, limit
    """
    with create_span("generate_query", input={"intent": intent, "context": context}) as span:
        tool = intent.get("tool")
        
        if tool == "search_flights":
            query_spec = generate_flight_query(intent, context)
        elif tool == "search_hotels":
            query_spec = generate_hotel_query(intent, context)
        elif tool == "recommend_food":
            query_spec = generate_restaurant_query(intent, context)
        else:
            query_spec = None
        
        span.update(output=query_spec)
        return query_spec


def generate_flight_query(intent: dict, context: dict) -> dict:
    """
    Generate MongoDB query for flights using LLM.
    """
    args = intent.get("args", {})
    
    # Extract parameters
    source = args.get("source") or context.get("source")
    destination = args.get("destination") or context.get("destination")
    dates = args.get("dates") or context.get("dates")
    budget = args.get("budget") or context.get("budget")
    filters = args.get("filters", {})
    
    # Build prompt for LLM
    prompt = f"""You are a MongoDB query generator for a flights database.

DATABASE SCHEMA:
{DATABASE_SCHEMA.split('HOTELS')[0]}

USER REQUEST:
- Source city: {source or 'not specified'}
- Destination city: {destination or 'not specified'}
- Dates: {dates or 'not specified'}
- Budget: {budget or 'not specified'}
- Filters: {json.dumps(filters)}

TASK: Generate a MongoDB query to find matching flights.

RULES:
1. Always filter by source_city and destination_city if provided
2. If budget specified, filter by price <= budget
3. If filters contain max_stops, filter by stops <= max_stops
4. If filters contain class preference, filter by class
5. Sort by: cheapest → price ascending, expensive → price descending, fastest → duration
6. Limit results to 10

OUTPUT FORMAT (JSON only):
{{
  "collection": "flights",
  "query": {{"destination_city": "Delhi", "price": {{"$lte": 6000}}}},
  "sort": {{"price": 1}},
  "limit": 10
}}

Generate the query:"""

    print(f"[QUERY GEN] Generating flight query...")
    print(f"[QUERY GEN] Source: {source}, Dest: {destination}, Budget: {budget}")
    
    raw_response = call_ollama(prompt, timeout=20)
    
    if not raw_response:
        # Fallback: build query programmatically
        return build_flight_query_fallback(source, destination, budget, filters)
    
    # Extract JSON
    query_spec = extract_json(raw_response)
    
    if not query_spec:
        # Fallback
        return build_flight_query_fallback(source, destination, budget, filters)
    
    print(f"[QUERY GEN] Generated query: {json.dumps(query_spec, indent=2)}")
    return query_spec


def build_flight_query_fallback(source, destination, budget, filters):
    """Fallback: programmatically build flight query."""
    query = {}
    
    if source:
        query["source_city"] = source
    if destination:
        query["destination_city"] = destination
    if budget:
        query["price"] = {"$lte": int(budget)}
    if filters.get("max_stops") is not None:
        query["stops"] = {"$lte": filters["max_stops"]}
    if filters.get("class"):
        query["class"] = filters["class"]
    
    # Sorting
    sort = {}
    if filters.get("price_preference") == "cheapest":
        sort = {"price": 1}
    elif filters.get("price_preference") == "expensive":
        sort = {"price": -1}
    elif filters.get("duration_preference") == "shortest":
        sort = {"duration": 1}
    else:
        sort = {"price": 1}  # Default: cheapest
    
    return {
        "collection": "flights",
        "query": query,
        "sort": sort,
        "limit": 10
    }


def generate_hotel_query(intent: dict, context: dict) -> dict:
    """Generate MongoDB query for hotels."""
    args = intent.get("args", {})
    
    city = args.get("destination") or context.get("destination")
    budget = args.get("budget") or context.get("budget")
    
    query = {}
    
    if city:
        query["city"] = city
    if budget:
        query["price_per_night"] = {"$lte": int(budget)}
    
    return {
        "collection": "hotels",
        "query": query,
        "sort": {"rating": -1},  # Best rated first
        "limit": 10
    }


def generate_restaurant_query(intent: dict, context: dict) -> dict:
    """Generate MongoDB query for restaurants."""
    args = intent.get("args", {})
    
    city = args.get("destination") or context.get("destination")
    preference = args.get("preference")
    
    query = {}
    
    if city:
        query["city"] = city
    
    # Handle preferences
    if preference:
        pref_lower = preference.lower()
        if "vegetarian" in pref_lower or "vegan" in pref_lower:
            query["vegetarian"] = True
        elif "fine dining" in pref_lower or "fancy" in pref_lower:
            query["fine_dining"] = True
        elif "budget" in pref_lower or "cheap" in pref_lower:
            query["price_range"] = {"$in": ["$", "$$"]}
    
    return {
        "collection": "restaurants",
        "query": query,
        "sort": {"rating": -1},
        "limit": 10
    }


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response."""
    if not text:
        return None
    
    text = text.strip()
    
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Remove markdown
    if '```' in text:
        import re
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    
    # Find JSON object
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
    
    return None