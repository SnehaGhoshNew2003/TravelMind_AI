# frontend.py (stable, POST-only, session-state initialized, no blinking)
import streamlit as st
import requests
from streamlit_folium import st_folium
import folium
from datetime import date

# -----------------------------
# SESSION STATE INITIALIZATION
# (must be at top-level, runs before UI)
# -----------------------------
st.session_state.setdefault("route_data", None)
st.session_state.setdefault("route_map_visible", False)
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("last_itinerary", None)
st.session_state.setdefault("last_weather", None)

# ===============================
# Configuration
# ===============================
API_URL = "http://127.0.0.1:8000"  # change if deployed elsewhere
#REQUEST_TIMEOUT = 60  # seconds

st.set_page_config(page_title="TravelMind AI", layout="wide")
st.title("🧭 AI-Powered Travel Assistant")
st.markdown("Explore places, get weather, calculate distances, and plan trips using AI.")


# -----------------------
# Helper: POST request wrapper
# -----------------------
def post_request(endpoint: str, payload: dict):
    try:
        resp = requests.post(f"{API_URL}/{endpoint}", json=payload) #, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"API Error {resp.status_code}: {resp.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error (endpoint: {endpoint}): {e}")
        return None

# -----------------------
# Sidebar navigation
# -----------------------
st.sidebar.title("🔍 Navigation")
tab = st.sidebar.radio(
    "Choose a feature",
    [
        "💬 Chat with AI",
        "🔎 Place Description",
        "🏙️ Nearby Attractions",
        "☀️ Weather Info",
        "📏 Distance Finder",
        "🗺️ Route Planner",
        "🧠 Smart Itinerary"
    ],
)

# -----------------------
# Chat tab (POST /ask)
# -----------------------
if tab == "💬 Chat with AI":
    st.header("💬 Chat with the AI Travel Assistant")

    # show history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**AI:** {msg['content']}")

    query = st.text_area("Type your message...", height=100, placeholder="E.g., 'Show nearby attractions in Delhi within 5 km'")

    if st.button("Send"):
        if not query.strip():
            st.warning("Please enter a message.")
        else:
            st.session_state.chat_history.append({"role": "user", "content": query})
            with st.spinner("AI is thinking..."):
                res = post_request("ask", {"query": query})
                if res:
                    ai_text = res.get("response") or res.get("answer") or str(res)
                    st.session_state.chat_history.append({"role": "ai", "content": ai_text})
                    st.rerun()

# -----------------------
# Place description (/place_description)
# -----------------------
elif tab == "🔎 Place Description":
    st.header("Get Short Place Description (Wikipedia)")
    place = st.text_input("Place name", "Kolkata")
    if st.button("Get Description"):
        payload = {"place_name": place}
        data = post_request("place_description", payload)
        if data:
            desc = data.get("description") or str(data)
            st.write(desc)

            
# -----------------------
# Nearby Attraction  (/nearby)
# -----------------------
elif tab == "🏙️ Nearby Attractions":
    st.header("🌍 Find Nearby Places")

    # user input
    place = st.text_input("Enter city / place", "Kolkata")
    radius = st.slider("Search Radius (km)", 0.1, 1.0, 0.5, step=0.1)

    # Search button
    if st.button("Search Nearby"):
        payload = {
            "place_name": place,
            "radius_km": float(radius)
        }

        with st.spinner("Fetching nearby places..."):
            data = post_request("nearby", payload)

        if not data:
            st.error("No response from backend.")
            st.stop()

        result = data.get("nearby_places")

        # If backend returns an error string
        if isinstance(result, str):
            st.error(result)
            st.stop()

        # EMPTY LIST
        if len(result) == 0:
            st.warning(f"No nearby places found within {radius} km of **{place}**.")
            st.stop()

        # SUCCESS
        st.success(f"Found {len(result)} places within {radius} km of **{place}**")

        st.write("")

        # Display results in readable cards
        for idx, item in enumerate(result, 1):
            name = item.get("name", "Unnamed place")
            dist = f"{item.get('distance_km', 0):.2f} km"
            st.write(f"**{idx}. {name}** — {dist}")




# -----------------------
# Weather Info 
# -----------------------
elif tab == "☀️ Weather Info":
    st.header("Weather Forecast / Current Weather")

    city = st.text_input("City name", "Kolkata")
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("Start date", value=None)
    with col2:
        date_to = st.date_input("End date", value=None)

    start_date = date_from.isoformat() if isinstance(date_from, date) else None
    end_date = date_to.isoformat() if isinstance(date_to, date) else None

    if st.button("Get Weather"):
        payload = {"city": city, "start_date": start_date, "end_date": end_date}
        data = post_request("weather", payload)

        if data:
            raw_weather = data.get("weather")

            # If backend returns plain text → parse & display nicely
            if isinstance(raw_weather, str):

                lines = raw_weather.strip().split("\n")

                # First line = Main heading
                st.subheader(lines[0])

                # If forecast format
                if "→" in lines[0] and len(lines) > 1:
                    # Create a clean weather table
                    table_data = []
                    for line in lines[1:]:
                        try:
                            date_part, rest = line.split(":", 1)
                            parts = rest.split("/")
                            max_t = parts[0].replace("Max", "").replace("°C", "").strip()
                            min_t = parts[1].replace("Min", "").replace("°C", "").strip()
                            rain = parts[2].replace("Rain", "").replace("mm", "").strip()
                            #code = parts[3].replace("Code", "").strip()

                            table_data.append({
                                "Date": date_part.strip(),
                                "Max Temp (°C)": max_t,
                                "Min Temp (°C)": min_t,
                                "Rain (mm)": rain,
                                #"Code": code
                            })
                        except:
                            pass

                    st.table(table_data)

                else:
                    # If single day / current weather → just display text
                    st.text(raw_weather)

            else:
                # If backend ever sends JSON instead
                st.json(raw_weather)


# -----------------------
# Distance Finder (/distance)
# -----------------------
elif tab == "📏 Distance Finder":
    st.header("Distance Between Two Places")
    c1, c2 = st.columns(2)
    with c1:
        place1 = st.text_input("From", "Kolkata")
    with c2:
        place2 = st.text_input("To", "Darjeeling")
    if st.button("Calculate"):
        payload = {"place1": place1, "place2": place2}
        data = post_request("distance", payload)
        if data:
            # your backend returns {"distance": "..."} or a string - handle both
            dist = data.get("distance") or data.get("distance_km") or str(data)
            st.success(dist)

# ===============================
# 🗺️ Route Planner (Stable Map)
# ===============================
elif tab == "🗺️ Route Planner":
    st.header("🗺️ Best Route Planner")

    city = st.text_input("Enter base city:", key="route_city")
    places_input = st.text_area(
        "Enter attractions (comma-separated):",
        placeholder="Example: Victoria Memorial, Howrah Bridge, Indian Museum",
        key="route_places"
    )

    # Run route finder
    if st.button("Find Best Route", key="route_button"):
        if not city.strip() or not places_input.strip():
            st.warning("Please enter both city and attractions.")
        else:
            places = [p.strip() for p in places_input.split(",") if p.strip()]
            with st.spinner("Finding best route..."):
                try:
                    response = requests.post(
                        f"{API_URL}/best_route",
                        json={"city": city, "places": places},
                        #timeout=REQUEST_TIMEOUT
                    )
                    if response.status_code == 200:
                        st.session_state.route_data = response.json()
                        st.session_state.route_map_visible = True
                    else:
                        st.error(f"API Error: {response.status_code} — {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection failed: {e}")

    # Render saved result (persistent across reruns)
    if st.session_state.get("route_map_visible") and st.session_state.get("route_data"):
        data = st.session_state.route_data
        st.subheader("📝 Best Route Summary")
        st.success(data.get("best_route") or data.get("route_info") or "No route information available.")
        ai_description = data.get("description")
        if ai_description:
            st.subheader("💡 Suggested Route Instructions")
            st.info(ai_description)

        coords = data.get("coordinates", [])
        if coords and isinstance(coords, list) and len(coords) > 0:
            m = folium.Map(location=[coords[0]["lat"], coords[0]["lon"]], zoom_start=8)
            for i, c in enumerate(coords):
                folium.Marker(
                    [c["lat"], c["lon"]],
                    tooltip=f"Stop {i+1}",
                    popup=c.get("name", f"Stop {i+1}")
                ).add_to(m)
            folium.PolyLine([(c["lat"], c["lon"]) for c in coords], weight=3, color="blue").add_to(m)
            st_folium(m, width=700, height=500)
        else:
            st.info("No coordinates returned to plot the route.")

# -----------------------
# Smart Itinerary (/generate_itinerary)
# -----------------------
elif tab == "🧠 Smart Itinerary":
    st.header("AI Trip Itinerary Generator")
    location = st.text_input("Location", "Kolkata")
    days = st.number_input("Days", min_value=1, max_value=14, value=3)
    interests = st.text_input("Interests (comma-separated)", "culture, food")
    budget = st.selectbox("Budget", ["Low", "Medium", "High"])
    mode = st.selectbox("Mode", ["Car", "Walk", "Public Transport", "Bike"])

    if st.button("Generate Itinerary"):
        payload = {"city": location, "days": int(days), "interests": interests, "budget": budget, "mode": mode}
        data = post_request("generate_itinerary", payload)
        if data:
            st.session_state.last_itinerary = data.get("itinerary")
            if st.session_state.last_itinerary:
                st.markdown(st.session_state.last_itinerary)
            else:
                st.info("No itinerary returned.")

# -----------------------
# Footer note
# -----------------------
st.markdown("---")
st.caption("Make sure your FastAPI backend is running (uvicorn main:app --reload) and accessible at API_URL.")
