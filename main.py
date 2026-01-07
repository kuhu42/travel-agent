from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import traceback
import json
import asyncio

from agent.agent import travel_agent
from memory.mongo_store import (
    start_conversation,
    get_context,
    save_turn,
    get_conversation_history,
    get_full_conversation
)

from langfuse_config import LANGFUSE_ENABLED, create_span

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    FIXED: Server-Sent Events (SSE) endpoint for streaming chat.
    """
    async def event_generator():
        try:
            print(f"\n[SSE] === Starting Stream ===")
            print(f"[SSE] Message: {req.message}")
            print(f"[SSE] Conversation ID: {req.conversation_id}")
            
            # Start or get conversation
            if not req.conversation_id:
                convo_id = start_conversation()
                print(f"[SSE] New conversation: {convo_id}")
                yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': convo_id})}\n\n"
                await asyncio.sleep(0.1)
            else:
                convo_id = req.conversation_id
                print(f"[SSE] Existing conversation: {convo_id}")
            
            # Get context
            context = get_context(convo_id)
            print(f"[SSE] Context: {context}")
            yield f"data: {json.dumps({'type': 'context', 'context': context})}\n\n"
            await asyncio.sleep(0.1)
            
            # Status update
            yield f"data: {json.dumps({'type': 'status', 'status': 'Thinking...'})}\n\n"
            await asyncio.sleep(0.2)
            
            # Process through agent
            response = travel_agent(req.message, context, convo_id)
            print(f"[SSE] Agent response: {response}")
            
            # Send reasoning
            if response.get("reasoning"):
                yield f"data: {json.dumps({'type': 'reasoning', 'reasoning': response['reasoning']})}\n\n"
                await asyncio.sleep(0.1)
            
            # Stream message character by character
            message = response.get("message", "")
            print(f"[SSE] Streaming message: {message[:50]}...")
            
            for i, char in enumerate(message):
                yield f"data: {json.dumps({'type': 'message_chunk', 'chunk': char, 'position': i})}\n\n"
                await asyncio.sleep(0.01)  # Typing effect
            
            # Send results if any
            results = response.get("results", [])
            if results:
                print(f"[SSE] Sending {len(results)} results")
                for idx, result in enumerate(results):
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool': result.get('tool'), 'result': result, 'index': idx})}\n\n"
                    await asyncio.sleep(0.2)
            
            # Complete
            yield f"data: {json.dumps({'type': 'complete', 'response': response})}\n\n"
            
            # Save conversation
            tools_used_str = ", ".join(response.get("tools_used", [])) if response.get("tools_used") else None
            save_turn(convo_id, req.message, response["message"], tools_used_str, response.get("reasoning", ""))
            
            # Updated context
            updated_context = get_context(convo_id)
            yield f"data: {json.dumps({'type': 'context_updated', 'context': updated_context})}\n\n"
            
            print(f"[SSE] === Stream Complete ===\n")
            
        except Exception as e:
            print(f"[SSE] ERROR: {str(e)}")
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.post("/chat")
def chat(req: ChatRequest):
    """Non-streaming endpoint (backward compatibility)."""
    try:
        print(f"\n=== New Chat Request ===")
        print(f"Message: {req.message}")
        print(f"Conversation ID: {req.conversation_id}")
        
        if not req.conversation_id:
            convo_id = start_conversation()
            print(f"Started new conversation: {convo_id}")
        else:
            convo_id = req.conversation_id
        
        context = get_context(convo_id)
        print(f"Context: {context}")
        
        response = travel_agent(req.message, context, convo_id)
        print(f"Agent response: {response}")
        
        tools_used_str = ", ".join(response.get("tools_used", [])) if response.get("tools_used") else None
        save_turn(convo_id, req.message, response["message"], tools_used_str, response.get("reasoning", ""))
        
        updated_context = get_context(convo_id)
        
        result = {
            "conversation_id": convo_id,
            "reply": response,
            "context": updated_context
        }
        
        return result
    
    except Exception as e:
        print(f"\n=== ERROR ===")
        print(f"Error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/{conversation_id}")
def get_conversation(conversation_id: str):
    """Retrieve full conversation details."""
    try:
        convo = get_full_conversation(conversation_id)
        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found")
        convo.pop("_id", None)
        return convo
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/{conversation_id}/history")
def get_history(conversation_id: str, limit: int = 10):
    """Get conversation history."""
    try:
        history = get_conversation_history(conversation_id, limit)
        return {"conversation_id": conversation_id, "history": history}
    except Exception as e:
        print(f"Error in get_history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/conversation/new")
def new_conversation():
    """Start a new conversation."""
    try:
        convo_id = start_conversation()
        return {"conversation_id": convo_id}
    except Exception as e:
        print(f"Error in new_conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "langfuse_enabled": LANGFUSE_ENABLED,
        "streaming_enabled": True
    }


@app.get("/langfuse-status")
def langfuse_status():
    """Check Langfuse integration status."""
    return {
        "enabled": LANGFUSE_ENABLED,
        "message": "Langfuse logging active" if LANGFUSE_ENABLED else "Langfuse not configured"
    }


# Static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")