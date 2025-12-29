def search_flights(destination, dates, budget=None):
    """
    Search for flight options to a destination.
    
    Args:
        destination: City/country to fly to
        dates: Travel dates
        budget: Optional budget constraint
    """
    flights = [
        {"airline": "Indigo", "price": 6200, "stops": 0, "duration": "2h 30m"},
        {"airline": "Vistara", "price": 7200, "stops": 1, "duration": "4h 15m"},
        {"airline": "Air India", "price": 5800, "stops": 1, "duration": "5h 00m"},
        {"airline": "SpiceJet", "price": 5500, "stops": 2, "duration": "6h 30m"}
    ]
    
    # Filter by budget if provided
    if budget:
        try:
            budget_num = float(budget)
            flights = [f for f in flights if f["price"] <= budget_num]
        except (ValueError, TypeError):
            pass
    
    return flights