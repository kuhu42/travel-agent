from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import traceback

from agent.agent import travel_agent
from memory.mongo_store import (
    start_conversation,
    get_context,
    save_turn,
    get_conversation_history,
    get_full_conversation
)

# Import Langfuse context manager helpers
from langfuse_config import LANGFUSE_ENABLED, create_span, flush

app = FastAPI()

# Add CORS middleware
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


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Main chat endpoint with Langfuse trace tracking using context manager.
    Each chat request creates a complete trace in Langfuse.
    """
    with create_span(
        "chat_endpoint",
        input={"message": req.message, "conversation_id": req.conversation_id},
        metadata={"endpoint": "/chat", "method": "POST"}
    ) as chat_span:
        
        try:
            print(f"\n=== New Chat Request ===")
            print(f"Message: {req.message}")
            print(f"Conversation ID: {req.conversation_id}")
            
            # Start new conversation or use existing
            if not req.conversation_id:
                convo_id = start_conversation()
                print(f"Started new conversation: {convo_id}")
            else:
                convo_id = req.conversation_id
            
            # Update span with conversation context
            chat_span.update(
                metadata={
                    "conversation_id": convo_id,
                    "is_new_conversation": not req.conversation_id
                }
            )
            
            # Get current context
            context = get_context(convo_id)
            print(f"Context: {context}")
            
            # Process message through agent (fully instrumented)
            response = travel_agent(req.message, context, convo_id)
            print(f"Agent response: {response}")
            
            # Save the turn with all tools used
            tools_used_str = ", ".join(response.get("tools_used", [])) if response.get("tools_used") else None
            
            save_turn(
                convo_id,
                req.message,
                response["message"],
                tools_used_str,
                response.get("reasoning", "")
            )
            
            # Get updated context
            updated_context = get_context(convo_id)
            
            result = {
                "conversation_id": convo_id,
                "reply": response,
                "context": updated_context
            }
            
            # Update span with final result
            chat_span.update(
                output=result,
                metadata={
                    "tools_used": response.get("tools_used", []),
                    "num_results": len(response.get("results", []))
                }
            )
            
            return result
        
        except Exception as e:
            print(f"\n=== ERROR ===")
            print(f"Error: {str(e)}")
            traceback.print_exc()
            
            # Log error to span
            chat_span.update(
                output={"error": str(e)},
                level="ERROR",
                status_message=str(e),
                metadata={"error_type": type(e).__name__}
            )
            
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/{conversation_id}")
def get_conversation(conversation_id: str):
    """Retrieve full conversation details."""
    with create_span(
        "get_conversation",
        input={"conversation_id": conversation_id}
    ) as span:
        try:
            convo = get_full_conversation(conversation_id)
            if not convo:
                span.update(
                    level="WARNING",
                    status_message="Conversation not found"
                )
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            convo.pop("_id", None)
            span.update(output={"conversation": convo})
            return convo
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error in get_conversation: {str(e)}")
            span.update(
                level="ERROR",
                status_message=str(e)
            )
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/{conversation_id}/history")
def get_history(conversation_id: str, limit: int = 10):
    """Get conversation history."""
    with create_span(
        "get_history",
        input={"conversation_id": conversation_id, "limit": limit}
    ) as span:
        try:
            history = get_conversation_history(conversation_id, limit)
            result = {"conversation_id": conversation_id, "history": history}
            span.update(output=result)
            return result
            
        except Exception as e:
            print(f"Error in get_history: {str(e)}")
            span.update(
                level="ERROR",
                status_message=str(e)
            )
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/conversation/new")
def new_conversation():
    """Start a new conversation."""
    with create_span("new_conversation") as span:
        try:
            convo_id = start_conversation()
            result = {"conversation_id": convo_id}
            span.update(output=result)
            return result
            
        except Exception as e:
            print(f"Error in new_conversation: {str(e)}")
            span.update(
                level="ERROR",
                status_message=str(e)
            )
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "langfuse_enabled": LANGFUSE_ENABLED
    }


@app.get("/langfuse-status")
def langfuse_status():
    """Check Langfuse integration status."""
    return {
        "enabled": LANGFUSE_ENABLED,
        "message": "Langfuse logging active" if LANGFUSE_ENABLED else "Langfuse not configured"
    }


# ---------- SHUTDOWN HANDLER ----------
@app.on_event("shutdown")
def shutdown_event():
    """Flush Langfuse events on application shutdown."""
    print("Shutting down, flushing Langfuse events...")
    flush()
    print("Langfuse events flushed")


# ---------- STATIC FILES ----------
app.mount("/", StaticFiles(directory="static", html=True), name="static")