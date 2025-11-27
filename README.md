# 🌍 TravelMind AI  
### **AI-Powered Tour Guide & Intelligent Route Planner**  
*(Built with LangChain, FastAPI, Streamlit, RAG, Overpass API & OpenTripMap API)*

TravelMind AI is a smart, end-to-end travel assistant that finds **real places**, generates **detailed descriptions**, and creates the **best possible travel route** for any city in the world.

This project integrates:
- **LLM-powered multi-agent reasoning**
- **Real data from OpenTripMap**
- **Custom LangChain tools**
- **FastAPI backend**
- **Streamlit frontend**

---

## 🚀 Features

### 🗺️ **Real-Time Place Discovery**
- Fetches *real* and *verified* places from OpenTripMap.
- Supports categories like museums, parks, malls, attractions, landmarks, etc.
- Returns:
  - Place name  
  - Category  
  - Popularity score  
  - Coordinates  
  - Real description  

---

### 🧠 **AI Agent With Multiple Tools**
TravelMind AI uses a LangChain agent equipped with custom tools:

- `get_real_places()` → Fetch popular places in a city  
- `get_place_details()` → Fetch descriptions & info  
- `plan_route()` → Generate the best travel route  
- `analyze_preferences()` → User preference filtering  

The agent decides which tool to run based on the user query.

---

### 🛣️ **Smart Route Planner**
- Calculates the best route using GPS coordinates.
- Minimizes travel time.
- Works for any city worldwide.

---

### 💬 **Interactive Streamlit UI**
Users can:
- Search for popular places  
- Filter by categories  
- Ask for place descriptions  
- Generate a complete route plan  
- Chat with the AI naturally  

---

### ⚙️ **FastAPI Backend**
Handles:
- Agent execution  
- Tool routing  
- API calls to OpenTripMap  
- Error handling  
- Data validation  

Streamlit interacts with FastAPI to fetch all data.

---

## 🏗️ System Architecture

```
User  
↓  
Streamlit Frontend  
↓  
FastAPI Backend  
↓  
LangChain Agent  
↓  
Custom Tools (Places, Details, Route Planning)  
↓  
OpenTripMap API  
↓  
Response to User  
```

---

## 📁 Project Structure

```
📦 TOUR
├── Dockerfile
├── frontend.py          # Streamlit UI
├── main.py              # FastAPI backend
├── rag.py               # RAG pipeline (optional)
├── requirements.txt     # Project dependencies
├── tools.py             # Tools for places, details, route
├── .env                 # API keys (OpenTripMap)
└── venv/                # Virtual environment
```

---

## 🔧 Installation & Setup

### **1. Clone the repository**
```bash
git clone https://github.com/yourusername/TravelMind-AI.git
cd TravelMind-AI
```

### **2. Create environment file**
Inside the `backend` folder, create `.env`:

```
OPENTRIPMAP_API_KEY=your_api_key_here
```

### **3. Install dependencies**
```bash
pip install -r requirements.txt
```

---

## 🚦 Running the Project

### **Start Backend (FastAPI)**
```bash
uvicorn backend.main:app --reload
```

### **Start Frontend (Streamlit)**
```bash
streamlit run frontend/app.py
```

---

## 🧪 Example User Queries

- “Show me the best route for Bangalore with malls, parks, and historical places.”  
- “List the top 10 attractions in Delhi.”  
- “Give me a short description of Charminar.”  
- “Plan a one-day trip in Jaipur.”  

---

## 🛠️ Tech Stack

### **AI & Backend**
- Python  
- LangChain (Tool Agent)
- LangGraph
- FastAPI  
- OpenTripMap API
- Overpass API
- Pydantic  

### **Frontend**
- Streamlit  
- Requests  
- Pandas  

---

## ⭐ Highlights

- Uses **real API data only** — *zero hallucination*  
- Clean & verified category mapping  
- Robust multi-agent workflow  
- Production-level architecture  
- Great for **AI, Backend, and Full-Stack** resumes  

---

## 🔮 Future Enhancements

- Multi-day itinerary planner  
- Map rendering with Leaflet/Folium  
- Hotel & restaurant recommendations  
- Offline vector search using FAISS  
- User login & saved trips  

---

## 📬 Contact  

Feel free to reach out for deployment help, UI improvements, or documentation updates.
