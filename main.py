from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from rag import ask_rag
from tools import (
    plan_trip_tool,
    get_weather_tool,
    get_best_route_tool,
    find_nearby_tool,
    get_distance_tool,
    get_place_description
)
from tools import get_coordinates,find_nearby_places,generate_route_prompt

app = FastAPI(
    title="TravelMind AI",
    description="Explore attractions, plan trips, get weather updates, and find optimal routes using LangChain + Gemini.",
    version="1.2"
)

# ===========================
# Models
# ===========================
class QueryInput(BaseModel):
    query: str


class TripInput(BaseModel):
    city: str
    days: int
    interests: str
    budget: str
    mode: str


class WeatherInput(BaseModel):
    city: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None



class RouteInput(BaseModel):
    city: str
    places: list[str]


class NearbyRequest(BaseModel):
    place_name: str
    radius_km: float


class DistanceInput(BaseModel):
    place1: str
    place2: str


class PlaceDescriptionInput(BaseModel):
    place_name: str


# ===========================
# Routes
# ===========================
@app.get("/")
def home():
    return {"message": "Welcome to the AI-Powered Tour Guide API!"}


@app.post("/ask")
def ask_general(input_data: QueryInput):
    query = input_data.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        response = ask_rag(query)
        return {"query": query, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/place_description")
def place_description(input_data: PlaceDescriptionInput):
    try:
        response = get_place_description.invoke({
            "place_name": input_data.place_name
        })
        return {"place_name": input_data.place_name, "description": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
coords_cache = {}

@app.post("/nearby")
def nearby_places(req: NearbyRequest):
    place_name = req.place_name.strip()
    radius_km = float(req.radius_km)

    # Step 1: get coordinates safely
    if place_name in coords_cache:
        coords = coords_cache[place_name]
    else:
        coords = get_coordinates(place_name)
        if not coords:
            return {"nearby_places": f"Could not find coordinates for '{place_name}'."}
        coords_cache[place_name] = coords

    # Step 2: call the tool safely
    try:
        tool_result = find_nearby_places(place_name=place_name, radius_km=radius_km)
    except Exception as e:
        return {"nearby_places": f"Error fetching nearby places: {str(e)}"}

    # Step 3: parse the tool output
    result_list = []
    seen_names = set()  # for removing duplicates

    if isinstance(tool_result, str):
        lines = tool_result.split("\n")[1:]  # skip first line
        for line in lines:
            line = line.strip().lstrip("- ").strip()
            if "(" in line and "km" in line:
                name, dist_part = line.rsplit("(", 1)
                name = name.strip()
                if name in seen_names:
                    continue  # skip duplicate
                seen_names.add(name)
                dist = dist_part.replace("km)", "").strip()
                try:
                    dist = float(dist)
                except:
                    dist = 0.0
                result_list.append({"name": name, "distance_km": dist})
    else:
        # If tool returns structured data (list/dict)
        for item in tool_result:
            name = item.get("name", "").strip()
            if name in seen_names or not name:
                continue
            seen_names.add(name)
            dist = item.get("distance_km", 0.0)
            result_list.append({"name": name, "distance_km": dist})

    # Step 4: sort by distance
    result_list = sorted(result_list, key=lambda x: x["distance_km"])

    # Step 5: ensure at least 10 places (if available)
    if len(result_list) < 10 and isinstance(tool_result, list):
        # try increasing radius or adding more results if possible
        # for now we just return whatever is available
        pass

    return {"nearby_places": result_list[:10]}  # return max 10 places

@app.post("/distance")
def calculate_distance(input_data: DistanceInput):
    try:
        response = get_distance_tool.invoke({
            "place1": input_data.place1,
            "place2": input_data.place2
        })
        return {"place1": input_data.place1, "place2": input_data.place2, "distance": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/weather")
def get_weather(input_data: WeatherInput):
    try:
        response = get_weather_tool.invoke({
            "city": input_data.city,
            "start_date": input_data.start_date,
            "end_date": input_data.end_date
        })
        return {"city": input_data.city, "weather": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/best_route")
def best_route(input_data: RouteInput):
    try:
        # 1️⃣ Get the best route from the tool
        result = get_best_route_tool.invoke({
            "city": input_data.city,
            "places": input_data.places
        })

        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        # Extract the ordered list of places from the best route
        # The tool currently only returns text like "Best route: City → Place1 → Place2 ..."
        route_text = result.get("route_info", "")
        coords = result.get("coordinates", [])

        # Parse best_places from route string
        if "→" in route_text:
            parts = [p.strip() for p in route_text.split("→")]
            # Remove the starting city
            best_places = parts[1:] if parts[0].lower() == input_data.city.lower() else parts
        else:
            best_places = input_data.places  # fallback

        # 2️⃣ Generate prompt and ask RAG for human-like description
        prompt = generate_route_prompt(input_data.city, best_places)
        description = ask_rag(prompt) if prompt else ""

        # 3️⃣ Return full info
        return {
            "city": input_data.city,
            "best_route": route_text,
            "coordinates": coords,
            "description": description
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/generate_itinerary")
def generate_itinerary(input_data: TripInput):
    if input_data.days <= 0:
        raise HTTPException(status_code=400, detail="Days must be greater than zero.")

    try:
        response = plan_trip_tool.invoke({
            "city": input_data.city,
            "days": input_data.days,
            "interests": input_data.interests,
            "budget": input_data.budget,
            "mode": input_data.mode
        })
        return {"itinerary": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))