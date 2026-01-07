from agent.router import route
from tools.registry import TOOL_REGISTRY
from memory.mongo_store import update_context
import yaml
import asyncio

# Import Langfuse context manager helpers
from langfuse_config import LANGFUSE_ENABLED, create_span, flush

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

FALLBACK = config["agent"]["fallback_response"]


async def travel_agent_streaming(user_message, context, conversation_id):
    """
    Streaming version of travel agent that yields events in real-time.
    
    Event types:
    - status: Current operation status
    - reasoning: LLM reasoning
    - tool_start: Tool execution starting
    - tool_result: Tool execution result
    - message: Agent message chunk
    - complete: Final response
    """
    with create_span(
        "travel_agent_streaming",
        input={"message": user_message, "context": context},
        metadata={
            "conversation_id": conversation_id,
            "message_length": len(user_message),
            "streaming": True
        }
    ) as agent_span:
        
        try:
            # Yield status
            yield {"type": "status", "status": "Analyzing request..."}
            await asyncio.sleep(0.1)  # Small delay for UX
            
            # Get decision from router
            yield {"type": "status", "status": "Routing request..."}
            decision = route(user_message, context)
            
            # Yield reasoning
            if decision.get("reasoning"):
                yield {
                    "type": "reasoning",
                    "reasoning": decision["reasoning"]
                }
            
            # Log routing decision
            agent_span.update(
                metadata={
                    "routing_decision": decision.get("reasoning"),
                    "num_actions": len(decision.get("actions", []))
                }
            )
            
            # Handle context updates
            context_updates = decision.get("context_updates", {})
            if context_updates:
                merged_context = {**context, **context_updates}
                update_context(conversation_id, merged_context)
                yield {
                    "type": "context_update",
                    "updates": context_updates
                }
            
            # Get actions list
            actions = decision.get("actions", [])
            
            # If no actions, just return message
            if not actions:
                response = {
                    "message": decision.get("message", FALLBACK),
                    "results": [],
                    "tools_used": [],
                    "reasoning": decision.get("reasoning", "")
                }
                
                # Stream message word by word
                message = response["message"]
                for i, char in enumerate(message):
                    yield {
                        "type": "message_chunk",
                        "chunk": char,
                        "position": i
                    }
                    await asyncio.sleep(0.01)  # Typing effect
                
                agent_span.update(output=response)
                
                yield {
                    "type": "complete",
                    "response": response
                }
                return
            
            # Execute ALL actions with tracking
            results = []
            tools_used = []
            messages = []
            
            yield {"type": "status", "status": f"Executing {len(actions)} action(s)..."}
            
            for idx, action in enumerate(actions):
                # Notify tool start
                tool_name = action.get("tool")
                yield {
                    "type": "tool_start",
                    "tool": tool_name,
                    "args": action.get("args", {}),
                    "index": idx
                }
                
                await asyncio.sleep(0.2)  # Visual feedback
                
                tool_result = execute_tool_with_tracking(
                    action, 
                    idx, 
                    conversation_id
                )
                
                # Notify tool result
                yield {
                    "type": "tool_result",
                    "tool": tool_name,
                    "result": tool_result,
                    "index": idx
                }
                
                if tool_result.get("success"):
                    results.append({
                        "tool": tool_result["tool_name"],
                        "data": tool_result["result"],
                        "message": tool_result["message"]
                    })
                    tools_used.append(tool_result["tool_name"])
                    messages.append(tool_result["message"])
                else:
                    results.append({
                        "tool": tool_result["tool_name"],
                        "error": tool_result["error"]
                    })
                
                await asyncio.sleep(0.1)
            
            # Combine all messages
            combined_message = "\n\n".join(messages) if messages else "Here's what I found:"
            
            # Stream final message
            yield {"type": "status", "status": "Preparing response..."}
            for i, char in enumerate(combined_message):
                yield {
                    "type": "message_chunk",
                    "chunk": char,
                    "position": i
                }
                await asyncio.sleep(0.01)
            
            response = {
                "message": combined_message,
                "results": results,
                "tools_used": tools_used,
                "reasoning": decision.get("reasoning", "")
            }
            
            # Log final response
            agent_span.update(
                output=response,
                metadata={
                    "tools_executed": len(tools_used),
                    "success": True
                }
            )
            
            # Send complete event
            yield {
                "type": "complete",
                "response": response
            }
            
        except Exception as e:
            print(f"Error in travel_agent_streaming: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Log error
            agent_span.update(
                output={"error": str(e)},
                level="ERROR",
                status_message=str(e)
            )
            
            yield {
                "type": "error",
                "error": str(e)
            }


def travel_agent(user_message, context, conversation_id):
    """
    Non-streaming version of travel agent (for backward compatibility).
    """
    with create_span(
        "travel_agent",
        input={"message": user_message, "context": context},
        metadata={
            "conversation_id": conversation_id,
            "message_length": len(user_message)
        }
    ) as agent_span:
        
        try:
            # Get decision from router (also instrumented)
            decision = route(user_message, context)
            
            # Log routing decision
            agent_span.update(
                metadata={
                    "routing_decision": decision.get("reasoning"),
                    "num_actions": len(decision.get("actions", []))
                }
            )
            
            # Handle context updates
            context_updates = decision.get("context_updates", {})
            if context_updates:
                merged_context = {**context, **context_updates}
                update_context(conversation_id, merged_context)
            
            # Get actions list
            actions = decision.get("actions", [])
            
            # If no actions, just return message
            if not actions:
                response = {
                    "message": decision.get("message", FALLBACK),
                    "results": [],
                    "tools_used": [],
                    "reasoning": decision.get("reasoning", "")
                }
                agent_span.update(output=response)
                return response
            
            # Execute ALL actions with tracking
            results = []
            tools_used = []
            messages = []
            
            for idx, action in enumerate(actions):
                tool_result = execute_tool_with_tracking(
                    action, 
                    idx, 
                    conversation_id
                )
                
                if tool_result.get("success"):
                    results.append({
                        "tool": tool_result["tool_name"],
                        "data": tool_result["result"],
                        "message": tool_result["message"]
                    })
                    tools_used.append(tool_result["tool_name"])
                    messages.append(tool_result["message"])
                else:
                    results.append({
                        "tool": tool_result["tool_name"],
                        "error": tool_result["error"]
                    })
            
            # Combine all messages
            combined_message = "\n\n".join(messages) if messages else "Here's what I found:"
            
            response = {
                "message": combined_message,
                "results": results,
                "tools_used": tools_used,
                "reasoning": decision.get("reasoning", "")
            }
            
            # Log final response
            agent_span.update(
                output=response,
                metadata={
                    "tools_executed": len(tools_used),
                    "success": True
                }
            )
            
            return response
            
        except Exception as e:
            print(f"Error in travel_agent: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Log error
            agent_span.update(
                output={"error": str(e)},
                level="ERROR",
                status_message=str(e)
            )
            
            return {
                "message": f"I encountered an error: {str(e)}. Please try again.",
                "results": [],
                "tools_used": [],
                "reasoning": f"Error: {str(e)}"
            }


def execute_tool_with_tracking(action, idx, conversation_id):
    """
    Execute a single tool with Langfuse tracking using context manager.
    """
    tool_name = action.get("tool")
    args = action.get("args", {})
    tool_message = action.get("message", "")
    
    with create_span(
        "execute_tool",
        input={
            "tool": tool_name,
            "args": args
        },
        metadata={
            "tool_index": idx,
            "conversation_id": conversation_id
        }
    ) as tool_span:
        
        if tool_name not in TOOL_REGISTRY:
            error_result = {
                "success": False,
                "tool_name": tool_name,
                "error": f"Tool {tool_name} not available"
            }
            tool_span.update(
                output=error_result,
                level="WARNING",
                status_message=f"Tool {tool_name} not found"
            )
            return error_result
        
        # Execute the tool
        tool = TOOL_REGISTRY[tool_name]
        try:
            # Clean args (remove None values)
            clean_args = {k: v for k, v in args.items() if v is not None}
            result = tool(**clean_args)
            
            # Log success
            success_result = {
                "success": True,
                "tool_name": tool_name,
                "result": result,
                "message": tool_message
            }
            
            tool_span.update(
                output=success_result,
                metadata={
                    "result_count": len(result) if isinstance(result, list) else 1,
                    "success": True
                }
            )
            
            return success_result
            
        except Exception as e:
            print(f"Error executing {tool_name}: {str(e)}")
            
            # Log error
            error_result = {
                "success": False,
                "tool_name": tool_name,
                "error": str(e)
            }
            
            tool_span.update(
                output=error_result,
                level="ERROR",
                status_message=str(e)
            )
            
            return error_result