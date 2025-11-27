# rag.py
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode
from tools import (
    find_nearby_tool,
    get_distance_tool,
    get_place_description,
    plan_trip_tool,
    get_weather_tool,
    get_best_route_tool
)
from dotenv import load_dotenv
import os

# =======================================
# Load environment variables
# =======================================
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables!")

# Ensure Gemini uses the correct API key
os.environ["GOOGLE_API_KEY"] = api_key

# =======================================
# Define the State for LangGraph
# =======================================
class State(MessagesState):
    """
    Extends MessagesState.
    Stores conversation messages and tool call results.
    """
    pass

# =======================================
# Build LangGraph
# =======================================
graph = StateGraph(State)

# Initialize Gemini LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.3,
    google_api_key=api_key  # Explicitly passing key
)

def llm_node(state: State):
    """
    Processes messages through LLM.
    Handles both HumanMessage input and previous system messages.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"messages": []}

    response = llm.invoke(messages)
    return {"messages": [response]}
# =======================================
# Integrate Tools
# =======================================
tools_node = ToolNode([
    find_nearby_tool,
    get_distance_tool,
    get_place_description,
    plan_trip_tool,
    get_weather_tool,
    get_best_route_tool
])

# =======================================
# Add Nodes and Edges
# =======================================
graph.add_node("llm", llm_node)
graph.add_node("tools", tools_node)

# Flow: START → LLM → Tools → END
graph.add_edge(START, "llm")
graph.add_edge("llm", "tools")
graph.add_edge("tools", END)

# Compile the RAG app
rag_app = graph.compile()

# =======================================
# Helper Function: Ask RAG
# =======================================
def ask_rag(query: str) -> str:
    system_instruction = """
    You are an intelligent AI travel assistant that can answer user queries using tools:
    - get_weather_tool: for current weather
    - get_distance_tool: for distance between two places
    - get_best_route_tool: for best route between two places
    - find_nearby_tool: for nearby attractions
    - get_place_description: for describing any place
    - plan_trip_tool: for planning itineraries
    Always respond clearly and conversationally in English.
    """

    try:
        result = rag_app.invoke({
            "messages": [
                HumanMessage(role="system", content=system_instruction),
                HumanMessage(role="user", content=query)
            ]
        })

        if isinstance(result, dict) and "messages" in result:
            response = result["messages"][-1].content
        elif isinstance(result, list) and hasattr(result[-1], "content"):
            response = result[-1].content
        else:
            response = str(result)

        if not response.strip():
            response = "I'm sorry, I couldn't process that request. Please try rephrasing."

        return response

    except Exception as e:
        return f"⚠️ Error while processing your request: {str(e)}"
    


# =======================================
# (Optional) Run Standalone CLI for Testing
# =======================================
"""
if _name_ == "_main_":
    print("AI Tour Guide (RAG System) Ready! Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        answer = ask_rag(user_input)
        print("\nAssistant:", answer, "\n")
"""