from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.agent import travel_agent
from memory.mongo_store import (
    start_conversation,
    get_context,
    save_turn,
    get_conversation_history,
    get_full_conversation
)

app = FastAPI()

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- API ENDPOINTS ----------
class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None

class ConversationResponse(BaseModel):
    conversation_id: str
    context: dict
    history: list

@app.post("/chat")
def chat(req: ChatRequest):
    """Main chat endpoint that processes user messages."""
    try:
        # Start new conversation or use existing
        if not req.conversation_id:
            convo_id = start_conversation()
        else:
            convo_id = req.conversation_id
        
        # Get current context
        context = get_context(convo_id)
        
        # Process message through agent
        response = travel_agent(req.message, context, convo_id)
        
        # Save the turn
        save_turn(
            convo_id,
            req.message,
            response["message"],
            response.get("tool_used"),
            response.get("reasoning", "")
        )
        
        # Get updated context after processing
        updated_context = get_context(convo_id)
        
        return {
            "conversation_id": convo_id,
            "reply": response,
            "context": updated_context
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation/{conversation_id}")
def get_conversation(conversation_id: str):
    """Retrieve full conversation details."""
    convo = get_full_conversation(conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Remove MongoDB _id field
    convo.pop("_id", None)
    return convo

@app.get("/conversation/{conversation_id}/history")
def get_history(conversation_id: str, limit: int = 10):
    """Get conversation history."""
    history = get_conversation_history(conversation_id, limit)
    return {"conversation_id": conversation_id, "history": history}

@app.post("/conversation/new")
def new_conversation():
    """Start a new conversation."""
    convo_id = start_conversation()
    return {"conversation_id": convo_id}

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}

# ---------- STATIC FILES LAST ----------
app.mount("/", StaticFiles(directory="static", html=True), name="static")