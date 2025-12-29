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
