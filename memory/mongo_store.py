from pymongo import MongoClient
from uuid import uuid4
from datetime import datetime

client = MongoClient("mongodb://localhost:27017")
db = client["travel_agent"]
conversations = db["conversations"]

def start_conversation():
    """Create a new conversation with empty context."""
    convo_id = str(uuid4())
    conversations.insert_one({
        "conversation_id": convo_id,
        "created_at": datetime.utcnow(),
        "context": {
            "destination": None,
            "dates": None,
            "budget": None,
            "preferences": {}
        },
        "history": []
    })
    return convo_id

def get_context(convo_id):
    """Retrieve current context for a conversation."""
    convo = conversations.find_one({"conversation_id": convo_id})
    if not convo:
        return {
            "destination": None,
            "dates": None,
            "budget": None,
            "preferences": {}
        }
    return convo["context"]

def get_full_conversation(convo_id):
    """Get the entire conversation including history."""
    return conversations.find_one({"conversation_id": convo_id})

def update_context(convo_id, context):
    """Update the context for a conversation."""
    conversations.update_one(
        {"conversation_id": convo_id},
        {
            "$set": {
                "context": context,
                "updated_at": datetime.utcnow()
            }
        }
    )

def save_turn(convo_id, user_msg, agent_resp, tool, reasoning=""):
    """Save a conversation turn with metadata."""
    conversations.update_one(
        {"conversation_id": convo_id},
        {
            "$push": {
                "history": {
                    "timestamp": datetime.utcnow(),
                    "user": user_msg,
                    "agent": agent_resp,
                    "tool_used": tool,
                    "reasoning": reasoning
                }
            }
        }
    )

def get_conversation_history(convo_id, limit=10):
    """Get recent conversation history for context."""
    convo = conversations.find_one({"conversation_id": convo_id})
    if not convo or "history" not in convo:
        return []
    
    # Return last N turns
    history = convo["history"]
    return history[-limit:] if len(history) > limit else history