def search_flights(destination, dates, source=None, budget=None, filters=None):
    """
    Search for flight options to a destination.
    
    Args:
        destination: City/country to fly to
        dates: Travel dates
        source: Optional departure city
        budget: Optional budget constraint
        filters: Optional dict with filtering criteria:
            - price_preference: 'cheapest' or 'expensive'
            - max_stops: 0, 1, 2, etc.
            - duration_preference: 'shortest'
    """
    flights = [
        {"airline": "Indigo", "price": 6200, "stops": 0, "duration": "2h 30m", "duration_mins": 150},
        {"airline": "Vistara", "price": 7200, "stops": 1, "duration": "4h 15m", "duration_mins": 255},
        {"airline": "Air India", "price": 5800, "stops": 1, "duration": "5h 00m", "duration_mins": 300},
        {"airline": "SpiceJet", "price": 5500, "stops": 2, "duration": "6h 30m", "duration_mins": 390},
        {"airline": "GoAir", "price": 5300, "stops": 1, "duration": "4h 45m", "duration_mins": 285},
        {"airline": "AirAsia", "price": 4800, "stops": 2, "duration": "7h 15m", "duration_mins": 435},
    ]
    
    # Add source info to flights if provided
    if source:
        for flight in flights:
            flight["from"] = source
            flight["to"] = destination
    
    # Filter by budget if provided
    if budget:
        try:
            budget_num = float(budget)
            flights = [f for f in flights if f["price"] <= budget_num]
        except (ValueError, TypeError):
            pass
    
    # Apply filters if provided
    if filters:
        # Filter by stops
        if 'max_stops' in filters:
            max_stops = filters['max_stops']
            flights = [f for f in flights if f["stops"] <= max_stops]
        
        # Sort by price preference
        if filters.get('price_preference') == 'cheapest':
            flights = sorted(flights, key=lambda x: x["price"])
        elif filters.get('price_preference') == 'expensive':
            flights = sorted(flights, key=lambda x: x["price"], reverse=True)
        
        # Sort by duration
        if filters.get('duration_preference') == 'shortest':
            flights = sorted(flights, key=lambda x: x["duration_mins"])
    
    # If no results after filtering, return a message
    if not flights:
        return [{
            "message": f"No flights found matching your criteria. Try adjusting your filters.",
            "criteria": filters
        }]
    
    return flights