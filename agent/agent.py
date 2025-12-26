from agent.router import route
from tools.registry import TOOL_REGISTRY
from memory.mongo_store import update_context
import yaml
import json

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

FALLBACK = config["agent"]["fallback_response"]

def travel_agent(user_message, context, conversation_id):
    """
    Enhanced agent that reasons about user intent and manages context.
    """
    # Get decision from the routing/planning layer
    decision = route(user_message, context)
    
    # Handle context updates
    context_updates = decision.get("context_updates", {})
    if context_updates:
        merged_context = {**context, **context_updates}
        update_context(conversation_id, merged_context)
    
    action = decision.get("action", "respond")
    
    # If action is to clarify or just respond
    if action in ["clarify", "respond"]:
        return {
            "message": decision.get("message", FALLBACK),
            "result": None,
            "tool_used": None,
            "reasoning": decision.get("reasoning", "")
        }
    
    # If action is to call a tool
    if action == "tool_call":
        tool_name = decision.get("tool")
        args = decision.get("args", {})
        
        if tool_name not in TOOL_REGISTRY:
            return {
                "message": f"I wanted to use {tool_name}, but it's not available. {FALLBACK}",
                "result": None,
                "tool_used": None,
                "reasoning": decision.get("reasoning", "")
            }
        
        # Execute the tool
        tool = TOOL_REGISTRY[tool_name]
        try:
            result = tool(**args)
            
            return {
                "message": decision.get("message", f"Here's what I found using {tool_name}:"),
                "result": result,
                "tool_used": tool_name,
                "reasoning": decision.get("reasoning", "")
            }
        except Exception as e:
            return {
                "message": f"I encountered an error while searching: {str(e)}. Please try again.",
                "result": None,
                "tool_used": None,
                "reasoning": decision.get("reasoning", "")
            }
    
    # Fallback
    return {
        "message": FALLBACK,
        "result": None,
        "tool_used": None,
        "reasoning": ""
    }