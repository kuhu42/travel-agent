"""
Seed script to populate MongoDB with travel data.
Run once to initialize the database with sample data.
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
import random

client = MongoClient("mongodb://localhost:27017")
db = client["travel_agent"]

# Drop existing collections (fresh start)
db.flights.drop()
db.hotels.drop()
db.restaurants.drop()

print("🗄️  Seeding MongoDB with travel data...")

# ==================== FLIGHTS ====================
print("\n✈️  Seeding flights...")

airlines = ["Indigo", "Vistara", "Air India", "SpiceJet", "GoAir", "AirAsia"]
cities = {
    "Mumbai": ["Delhi", "Bangalore", "Goa", "Chennai", "Kolkata", "Hyderabad"],
    "Delhi": ["Mumbai", "Bangalore", "Goa", "Chennai", "Kolkata", "Jaipur"],
    "Bangalore": ["Mumbai", "Delhi", "Goa", "Chennai", "Hyderabad", "Pune"],
    "Goa": ["Mumbai", "Delhi", "Bangalore", "Chennai", "Pune"],
    "Chennai": ["Mumbai", "Delhi", "Bangalore", "Kolkata", "Hyderabad"],
}

flights = []
flight_id = 1

for source in cities.keys():
    for dest in cities[source]:
        for airline in airlines:
            # Generate multiple flights per route
            for _ in range(3):
                # Random departure time
                hour = random.randint(5, 22)
                minute = random.choice([0, 15, 30, 45])
                departure = f"{hour:02d}:{minute:02d}"
                
                # Random duration (1-6 hours)
                duration_hours = random.randint(1, 6)
                duration_mins = random.randint(0, 59)
                duration = f"{duration_hours}h {duration_mins}m"
                
                # Calculate arrival time
                arrival_hour = (hour + duration_hours) % 24
                arrival_minute = (minute + duration_mins) % 60
                arrival = f"{arrival_hour:02d}:{arrival_minute:02d}"
                
                # Random stops
                stops = random.choices([0, 1, 2], weights=[0.4, 0.4, 0.2])[0]
                
                # Random class
                flight_class = random.choice(["Economy", "Business"])
                
                # Price based on stops, class, duration
                base_price = 3000
                if stops == 0:
                    base_price += 1500
                if flight_class == "Business":
                    base_price *= 2.5
                base_price += duration_hours * 200
                
                # Add randomness
                price = int(base_price * random.uniform(0.8, 1.2))
                
                # Days left (1-90 days)
                days_left = random.randint(1, 90)
                
                flight = {
                    "index": flight_id,
                    "airline": airline,
                    "flight": f"{airline[:2].upper()}{random.randint(100, 999)}",
                    "source_city": source,
                    "departure_time": departure,
                    "stops": stops,
                    "arrival_time": arrival,
                    "destination_city": dest,
                    "class": flight_class,
                    "duration": duration,
                    "days_left": days_left,
                    "price": price
                }
                
                flights.append(flight)
                flight_id += 1

db.flights.insert_many(flights)
print(f"✅ Inserted {len(flights)} flights")

# Create indexes for faster queries
db.flights.create_index([("source_city", 1), ("destination_city", 1)])
db.flights.create_index("price")
db.flights.create_index("stops")
db.flights.create_index("class")

# ==================== HOTELS ====================
print("\n🏨 Seeding hotels...")

hotel_names = [
    "Grand Palace", "City Central", "Boutique Stay", "Budget Inn",
    "Luxury Resort", "Comfort Suites", "Heritage Hotel", "Modern Plaza",
    "Riverside Inn", "Mountain View", "Ocean Breeze", "Garden Paradise"
]

amenities_pool = [
    ["WiFi", "Breakfast", "Pool", "Gym", "Spa", "Restaurant"],
    ["WiFi", "Breakfast", "Pool", "Gym"],
    ["WiFi", "Breakfast", "Pool"],
    ["WiFi", "Breakfast"],
]

hotels = []
hotel_id = 1

for city in ["Mumbai", "Delhi", "Bangalore", "Goa", "Chennai", "Kolkata", "Jaipur", "Pune", "Hyderabad"]:
    for name in random.sample(hotel_names, 6):  # 6 hotels per city
        # Random rating (3.0 - 5.0)
        rating = round(random.uniform(3.0, 5.0), 1)
        
        # Price based on rating
        if rating >= 4.5:
            price = random.randint(8000, 15000)
            amenities = amenities_pool[0]
        elif rating >= 4.0:
            price = random.randint(5000, 8000)
            amenities = amenities_pool[1]
        elif rating >= 3.5:
            price = random.randint(3000, 5000)
            amenities = amenities_pool[2]
        else:
            price = random.randint(2000, 3000)
            amenities = amenities_pool[3]
        
        hotel = {
            "index": hotel_id,
            "name": f"{name} {city}",
            "city": city,
            "price_per_night": price,
            "rating": rating,
            "amenities": amenities
        }
        
        hotels.append(hotel)
        hotel_id += 1

db.hotels.insert_many(hotels)
print(f"✅ Inserted {len(hotels)} hotels")

# Create indexes
db.hotels.create_index("city")
db.hotels.create_index("price_per_night")
db.hotels.create_index("rating")

# ==================== RESTAURANTS ====================
print("\n🍽️  Seeding restaurants...")

restaurant_data = [
    # Fine Dining
    {"name": "Le Jules Verne", "cuisine": "French", "price_range": "$$$$", "rating": 4.7, "vegetarian": False, "fine_dining": True},
    {"name": "Epicure", "cuisine": "French", "price_range": "$$$$", "rating": 4.8, "vegetarian": False, "fine_dining": True},
    {"name": "The Golden Dragon", "cuisine": "Chinese", "price_range": "$$$$", "rating": 4.6, "vegetarian": False, "fine_dining": True},
    {"name": "Truffles", "cuisine": "Italian", "price_range": "$$$$", "rating": 4.7, "vegetarian": False, "fine_dining": True},
    
    # Casual
    {"name": "Cafe de Flore", "cuisine": "French Cafe", "price_range": "$$", "rating": 4.3, "vegetarian": False, "fine_dining": False},
    {"name": "Local Street Bistro", "cuisine": "Bistro", "price_range": "$", "rating": 4.0, "vegetarian": False, "fine_dining": False},
    {"name": "Pizza Paradise", "cuisine": "Italian", "price_range": "$$", "rating": 4.2, "vegetarian": True, "fine_dining": False},
    {"name": "Burger Joint", "cuisine": "American", "price_range": "$", "rating": 3.9, "vegetarian": False, "fine_dining": False},
    
    # Vegetarian
    {"name": "Gentle Gourmet", "cuisine": "Vegan", "price_range": "$$", "rating": 4.4, "vegetarian": True, "fine_dining": False},
    {"name": "Le Potager du Marais", "cuisine": "Vegetarian", "price_range": "$$", "rating": 4.2, "vegetarian": True, "fine_dining": False},
    {"name": "Green Leaf", "cuisine": "Vegetarian", "price_range": "$", "rating": 4.1, "vegetarian": True, "fine_dining": False},
    
    # Budget
    {"name": "Crepe Corner", "cuisine": "French Street Food", "price_range": "$", "rating": 4.1, "vegetarian": False, "fine_dining": False},
    {"name": "Dosa Delights", "cuisine": "South Indian", "price_range": "$", "rating": 4.3, "vegetarian": True, "fine_dining": False},
    {"name": "Noodle House", "cuisine": "Asian", "price_range": "$", "rating": 3.8, "vegetarian": False, "fine_dining": False},
]

restaurants = []
rest_id = 1

for city in ["Mumbai", "Delhi", "Bangalore", "Goa", "Chennai", "Kolkata", "Jaipur", "Pune", "Hyderabad"]:
    # Add variations of each restaurant to different cities
    for base_restaurant in restaurant_data:
        restaurant = {
            "index": rest_id,
            "name": f"{base_restaurant['name']} - {city}",
            "city": city,
            "cuisine": base_restaurant["cuisine"],
            "price_range": base_restaurant["price_range"],
            "rating": round(base_restaurant["rating"] + random.uniform(-0.2, 0.2), 1),
            "vegetarian": base_restaurant["vegetarian"],
            "fine_dining": base_restaurant["fine_dining"]
        }
        
        restaurants.append(restaurant)
        rest_id += 1

db.restaurants.insert_many(restaurants)
print(f"✅ Inserted {len(restaurants)} restaurants")

# Create indexes
db.restaurants.create_index("city")
db.restaurants.create_index("vegetarian")
db.restaurants.create_index("fine_dining")
db.restaurants.create_index("price_range")

print("\n✅ Database seeding complete!")
print(f"\nStatistics:")
print(f"  Flights: {db.flights.count_documents({})}")
print(f"  Hotels: {db.hotels.count_documents({})}")
print(f"  Restaurants: {db.restaurants.count_documents({})}")