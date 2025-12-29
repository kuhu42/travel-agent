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