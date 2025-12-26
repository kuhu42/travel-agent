# flight_tool.py
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


# hotel_tool.py
def search_hotels(destination, budget=None, dates=None):
    """
    Search for hotel options in a destination.
    
    Args:
        destination: City/location
        budget: Optional budget per night
        dates: Optional travel dates
    """
    hotels = [
        {
            "name": "Hotel Central",
            "price_per_night": 4500,
            "rating": 4.2,
            "amenities": ["WiFi", "Breakfast", "Pool"]
        },
        {
            "name": "Boutique Stay",
            "price_per_night": 6200,
            "rating": 4.5,
            "amenities": ["WiFi", "Breakfast", "Spa", "Gym"]
        },
        {
            "name": "Budget Inn",
            "price_per_night": 2800,
            "rating": 3.8,
            "amenities": ["WiFi", "Breakfast"]
        },
        {
            "name": "Luxury Resort",
            "price_per_night": 9500,
            "rating": 4.8,
            "amenities": ["WiFi", "Breakfast", "Spa", "Pool", "Gym", "Restaurant"]
        }
    ]
    
    # Filter by budget if provided
    if budget:
        try:
            budget_num = float(budget)
            hotels = [h for h in hotels if h["price_per_night"] <= budget_num]
        except (ValueError, TypeError):
            pass
    
    return hotels


# food_tool.py
def recommend_food(destination, preference=None):
    """
    Recommend restaurants in a destination.
    
    Args:
        destination: City/location
        preference: Optional preference (e.g., "vegetarian", "fine dining", "budget")
    """
    all_restaurants = {
        "fine dining": [
            {"name": "Le Jules Verne", "cuisine": "French", "price_range": "$$$$", "rating": 4.7},
            {"name": "Epicure", "cuisine": "French", "price_range": "$$$$", "rating": 4.8}
        ],
        "casual": [
            {"name": "Cafe de Flore", "cuisine": "French Cafe", "price_range": "$$", "rating": 4.3},
            {"name": "Local Street Bistro", "cuisine": "Bistro", "price_range": "$", "rating": 4.0}
        ],
        "vegetarian": [
            {"name": "Gentle Gourmet", "cuisine": "Vegan", "price_range": "$$", "rating": 4.4},
            {"name": "Le Potager du Marais", "cuisine": "Vegetarian", "price_range": "$$", "rating": 4.2}
        ],
        "budget": [
            {"name": "Local Street Bistro", "cuisine": "Bistro", "price_range": "$", "rating": 4.0},
            {"name": "Crepe Corner", "cuisine": "French Street Food", "price_range": "$", "rating": 4.1}
        ]
    }
    
    # Return based on preference
    if preference:
        pref_lower = preference.lower()
        for key in all_restaurants:
            if key in pref_lower:
                return all_restaurants[key]
    
    # Return a mix if no specific preference
    result = []
    for category in all_restaurants.values():
        result.extend(category[:1])  # Take first from each category
    
    return result