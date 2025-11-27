# tools.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import overpass
import wikipedia
import itertools
import requests
from dotenv import load_dotenv
import os

# ======================================
# Environment and API Setup
# ======================================
load_dotenv()
OPENTRIPMAP_API_KEY = os.getenv("OPENTRIPMAP_API_KEY")
api_key = os.getenv('GOOGLE_API_KEY')
os.environ["GOOGLE_API_KEY"] = api_key

# Initialize services
llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")
geolocator = Nominatim(user_agent="tour_planner_app")
overpass_api = overpass.API()
last_place_coords = None


# ======================================
# Helper: Get Coordinates of a Place
# ======================================
def get_coordinates(place_name: str):
    """Returns (latitude, longitude) of a place using Nominatim."""
    location = geolocator.geocode(place_name)
    if not location:
        return None
    return (location.latitude, location.longitude)

# ======================================
# Helper: Find Nearby Places via Overpass
# ======================================
def find_nearby_places(place_name: str, radius_km: float):
    """Queries Overpass API to find nearby points of interest."""
    global last_place_coords
    
    coords = get_coordinates(place_name)
    if not coords:
        return f"Could not find coordinates for '{place_name}'."

    last_place_coords = coords
    lat, lon = coords
    radius_m = radius_km * 1000

    query = f"""
    (
      node(around:{radius_m},{lat},{lon})["tourism"];
      node(around:{radius_m},{lat},{lon})["amenity"];
      node(around:{radius_m},{lat},{lon})["historic"];
    );
    out body;
    """

    try:
        data = overpass_api.get(query)
    except Exception:
        return "Overpass API request failed. Try again later."

    results = []
    for feature in data['features']:
        name = feature['properties'].get('name')
        if name:
            place_lat = feature['geometry']['coordinates'][1]
            place_lon = feature['geometry']['coordinates'][0]
            dist = geodesic((lat, lon), (place_lat, place_lon)).km
            results.append({"name": name, "distance_km": dist})

    results = sorted(results, key=lambda x: x["distance_km"])
    return results

# =======================================
# Helper: Generate human-like travel route prompt
# =======================================
def generate_route_prompt(city: str, best_places: list) -> str:
    """
    Creates a concise prompt to ask the RAG system for a friendly, human-readable route description.
    """
    if not best_places:
        return ""
    
    prompt = (
        f"Create a short, human-like travel plan for visiting these places starting from {city}: "
        + ", ".join(best_places) +
        ". Describe how a user can reach each destination, recommended transport methods, "
        "and make it friendly, concise, and practical."
    )
    return prompt

# ======================================
# Helper: Plan trip Wikivoyage
# ======================================

def get_travel_insights(city: str) -> str:
    """
    Real human-like travel advice from Wikivoyage.
    Includes: Best areas, safety, culture, transport tips.
    """
    try:
        params = {
            "action": "query",
            "prop": "extracts",
            "format": "json",
            "titles": city,
            "origin": "*",
            "formatversion": 2,
            "explaintext": 1
        }
        r = requests.get("https://en.wikivoyage.org/w/api.php", params=params).json()
        text = r.get("query", {}).get("pages", [{}])[0].get("extract", "")

        if not text:
            return f"No travel guide found for {city}."

        wanted = ["Understand", "Get in", "Get around", "Stay safe", "Eat", "Drink"]
        output = []

        for section in wanted:
            if section.lower() in text.lower():
                part = text.split(section,1)[-1]
                cleaned = part.split("\n\n",1)[-1].strip()
                output.append(f"### {section}\n{cleaned[:600].strip()}")

        return "\n\n".join(output) or text[:1200]

    except:
        return f"Failed to fetch travel guide for {city}."


def get_place_pros_cons(city: str) -> str:
    """
    Summarize pros, cons, and best time to visit using:
    - Wikipedia description
    - Wikivoyage travel insights
    (No hallucinated data; only summarize what is available.)
    """
    description = get_place_description.invoke({"place_name": city})
    insights = get_travel_insights(city)

    prompt = f"""
    You are a travel researcher.
    Using ONLY the information below, summarize realistically.

    Wikipedia Description:
    {description}

    Travel Insights (Wikivoyage):
    {insights}

    Now provide:
    1. Pros of visiting {city}
    2. Cons or cautions (if any)
    3. Best season or months to visit (infer from climate/safety/experience cues)
    4. Who this destination is best suited for (e.g., families / backpackers / couples / culture lovers)

    DO NOT add new attractions or invented claims.
    Only summarize logically from the given info.
    """

    response = llm.invoke(prompt)
    return response.content


def get_real_places(city: str, limit: int = 10) -> list:
    """
    Get real popular places with categories & popularity score
    from OpenTripMap (not hallucinated).
    """
    try:
        # Step 1: Get coordinates of city
        coord_url = f"https://geocode.maps.co/search?q={city}"
        geo = requests.get(coord_url).json()
        if not geo:
            return f"Could not find '{city}'."

        lat = geo[0]["lat"]
        lon = geo[0]["lon"]

        # Step 2: Fetch places nearby
        places_url = (
            f"https://api.opentripmap.com/0.1/en/places/radius?"
            f"radius=5000&lon={lon}&lat={lat}&limit={limit}&apikey={OPENTRIPMAP_API_KEY}"
        )
        data = requests.get(places_url).json()

        results = []
        for p in data.get("features", []):
            xid = p["properties"].get("xid")
            name = p["properties"].get("name")
            if not xid or not name:
                continue

            # Step 3: Get place details
            detail = requests.get(
                f"https://api.opentripmap.com/0.1/en/places/xid/{xid}?apikey={OPENTRIPMAP_API_KEY}"
            ).json()

            results.append({
                "name": name,
                "category": detail.get("kinds", "Unknown"),
                "popularity": detail.get("rate", "Unknown")
            })

        return results or "No real places found."

    except Exception as e:
        return f"Error fetching real places: {str(e)}"

# ======================================
# Tool 1: Find Nearby Places
# ======================================
@tool("find_nearby_tool")
def find_nearby_tool(place_name: str, radius_km: float) -> str:
    """Find nearby tourist or public attractions within a radius (km) of a place."""
    results = find_nearby_places(place_name, radius_km)

    if isinstance(results, str):
        return results
    if not results:
        return f"No nearby places found within {radius_km} km of {place_name}."

    response = [f"Nearby places within {radius_km} km of {place_name}:"]
    for r in results[:20]:
        response.append(f"- {r['name']} ({r['distance_km']:.2f} km)")
    return "\n".join(response)


# ======================================
# Tool 2: Get Place Description
# ======================================
@tool("get_place_description")
def get_place_description(place_name: str) -> str:
    """Fetch a short Wikipedia description for a given place."""
    try:
        summary = wikipedia.summary(place_name, sentences=3)
        return f"About {place_name}:\n{summary}"
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Multiple matches found for '{place_name}': {', '.join(e.options[:5])}"
    except wikipedia.exceptions.PageError:
        return f"No Wikipedia page found for '{place_name}'."


# ======================================
# Tool 3: Calculate Distance Between Two Places
# ======================================
@tool("calculate_distance_between_places")
def get_distance_tool(place1: str, place2: str) -> str:
    """Calculate straight-line distance (km) between two places using coordinates."""
    coords1 = get_coordinates(place1)
    coords2 = get_coordinates(place2)

    if not coords1 or not coords2:
        return "Could not resolve coordinates for one or both places."

    distance_km = geodesic(coords1, coords2).km
    return f"Distance between {place1} and {place2}: {distance_km:.2f} km"

# ======================================
# Tool 4: Gets the weather forcast of the place 
# ======================================
@tool("get_weather")
def get_weather_tool(city: str, start_date: str = None, end_date: str = None) -> str:
    """
    Fetches weather data for a city.
    - If both start_date and end_date are given → returns a forecast for that range.
    - If only one date is given → returns weather for that day.
    - If no date is given → returns current weather.
    """
    try:
        coords = get_coordinates(city)
        if not coords:
            return f"Could not find coordinates for '{city}'."
        lat, lon = coords

        # ---------- RANGE FORECAST ----------
        if start_date and end_date:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
                f"&timezone=auto&start_date={start_date}&end_date={end_date}"
            )
            r = requests.get(url, timeout=15).json()
            daily = r.get("daily", {})

            if not daily:
                return f"No forecast available for {city} between {start_date} and {end_date}."

            lines = [f"Weather Forecast for {city} ({start_date} → {end_date}):"]
            for i, date in enumerate(daily.get("time", [])):
                max_t = daily.get("temperature_2m_max", ["-"])[i]
                min_t = daily.get("temperature_2m_min", ["-"])[i]
                prec = daily.get("precipitation_sum", ["-"])[i]
                code = daily.get("weathercode", ["-"])[i]
                lines.append(f"{date}: Max {max_t}°C / Min {min_t}°C / Rain {prec}mm / Code {code}")
            return "\n".join(lines)

        # ---------- SINGLE DAY FORECAST ----------
        elif start_date:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
                f"&timezone=auto&start_date={start_date}&end_date={start_date}"
            )
            r = requests.get(url, timeout=15).json()
            daily = r.get("daily", {})
            if not daily:
                return f"No forecast available for {city} on {start_date}."
            return (
                f"Weather Forecast for {city} on {start_date}:\n"
                f"- Max Temp: {daily.get('temperature_2m_max', ['-'])[0]}°C\n"
                f"- Min Temp: {daily.get('temperature_2m_min', ['-'])[0]}°C\n"
                f"- Rainfall: {daily.get('precipitation_sum', ['-'])[0]} mm\n"
                f"- Code: {daily.get('weathercode', ['-'])[0]}"
            )

        # ---------- CURRENT WEATHER ----------
        else:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current_weather=true&timezone=auto"
            )
            r = requests.get(url, timeout=10).json()
            current = r.get("current_weather", {})
            return (
                f"Current Weather in {city}:\n"
                f"- Temperature: {current.get('temperature', '-') }°C\n"
                f"- Wind Speed: {current.get('windspeed', '-') } km/h\n"
                f"- Weather Code: {current.get('weathercode', '-')}"
            )

    except Exception as e:
        return f"Weather data unavailable: {str(e)}"


# ======================================
# Tool 5: Best Route Suggestion
# ======================================
@tool("get_best_route")
def get_best_route_tool(city: str, places: list) -> dict:
    """
    Suggests the best visiting route among given attractions near a city.
    Returns both readable text and coordinates for map visualization.
    """
    try:
        city_location = geolocator.geocode(city)
        if not city_location:
            return {"error": f"Couldn't find location for '{city}'."}

        city_coords = (city_location.latitude, city_location.longitude)

        # Get coordinates for each place
        valid_places = []
        for place in places:
            location = geolocator.geocode(place)
            if location:
                valid_places.append({
                    "name": place,
                    "coords": (location.latitude, location.longitude)
                })
            else:
                print(f"Warning: '{place}' not found, skipping...")

        if not valid_places:
            return {"error": "No valid places found. Please check your place names."}

        # Compute all possible routes
        routes = []
        for perm in itertools.permutations(valid_places):
            total_distance = 0
            prev = city_coords
            for p in perm:
                total_distance += geodesic(prev, p["coords"]).km
                prev = p["coords"]
            routes.append((total_distance, [p["name"] for p in perm]))

        # Find shortest route
        best = min(routes, key=lambda x: x[0])
        best_places = best[1]
        total_distance = best[0]

        # Collect coordinates for plotting (city + route)
        coords = [city_coords]
        for p in valid_places:
            if p["name"] in best_places:
                coords.append(p["coords"])

        # Prepare output
        route_str = " → ".join([city] + best_places)
        text = f"Best route: {route_str} (Total distance: {total_distance:.2f} km)"
        coord_list = [{"lat": c[0], "lon": c[1]} for c in coords]

        return {
            "route_info": text,
            "coordinates": coord_list
        }

    except Exception as e:
        return {"error": f"Error generating route: {str(e)}"}
    

# ======================================
# Tool 6: Plan Trip Itinerary 
# ======================================
@tool("plan_trip")
def plan_trip_tool(city: str, days: int, interests: str, budget: str, mode: str) -> str:
    """Generate a structured multi-day itinerary using nearby places & user preferences,
    including pros/cons info, estimated time to visit each attraction, and best season to visit."""

    # Step 1: Get nearby places (Overpass)
    nearby = find_nearby_places(city, 10)
    if isinstance(nearby, str) or not nearby:
        nearby_names = []
    else:
        nearby_names = [p['name'] for p in nearby[:10]]

    # Step 1b: Get popular real places (OpenTripMap)
    real_places = get_real_places(city, limit=10)
    if isinstance(real_places, str):
        real_names = []
    else:
        real_names = [p['name'] for p in real_places]

    # Combine all place names (deduplicate)
    all_places = list(dict.fromkeys(nearby_names + real_names))[:15]

    # Step 2: Gather pros/cons info for the main city
    city_pros_cons = get_place_pros_cons(city)

    # Step 3: Prepare LLM prompt including pros/cons info, best visiting season, and weather
    prompt = f"""
    You are a professional travel planner.
    Create a {days}-day travel itinerary for {city}.
    Include places of interest: {', '.join(all_places)}
    Interests: {interests}
    Budget: {budget}
    Travel mode: {mode}

    For the main city ({city}):
    Include the following pros/cons summary:
    {city_pros_cons}

    Also include:
    1. Best months or season to visit the city, highlighting peak and off-peak periods
    2. General weather conditions during the recommended months
    3. Suggested duration to spend at each attraction (hours or half-day/full-day)
    4. Travel time estimates between attractions
    5. Recommendations for food & cultural experiences

    For each day:
    - List 3 to 5 attractions with short descriptions
    - Include estimated visit time per attraction
    - Include travel time between attractions
    """

    response = llm.invoke(prompt)
    return response.content