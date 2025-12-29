import json
import yaml
import re
import hashlib
from llm.ollama_client import call_ollama
from langfuse_config import LANGFUSE_ENABLED, create_span, flush

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

SYSTEM_PROMPT = config["agent"]["system_prompt"]
USE_SCOPE_CACHE = config.get("routing", {}).get("cache_scope_checks", True)

# Simple in-memory cache for scope checks
SCOPE_CACHE = {}
MAX_CACHE_SIZE = 100


def route(user_message: str, context: dict) -> dict:
    """
    Enhanced routing with LLM-based scope detection.
    Uses Langfuse context manager for observability.
    """
    with create_span("router", input={"message": user_message, "context": context}) as span:
        try:
            # STEP 1: Quick heuristic check for obviously out-of-scope queries
            if is_obviously_out_of_scope(user_message):
                print("[ROUTER] Quick detection: OUT OF SCOPE")
                out_of_scope_response = {
                    "reasoning": "Query is not travel-related",
                    "actions": [],
                    "message": "I'm sorry, I can only help with travel planning - finding flights, hotels, and restaurant recommendations. I cannot answer math problems, coding questions, or general knowledge queries.",
                    "context_updates": {}
                }
                
                span.update(
                    output=out_of_scope_response,
                    metadata={"route_type": "out_of_scope_heuristic"}
                )
                
                return out_of_scope_response
            
            # STEP 2: For ambiguous cases, use LLM to check scope
            is_in_scope = check_scope_with_llm(user_message)
            
            if not is_in_scope:
                out_of_scope_response = {
                    "reasoning": "Query is not travel-related (LLM determined)",
                    "actions": [],
                    "message": "I'm sorry, I can only help with travel planning - finding flights, hotels, and restaurant recommendations.",
                    "context_updates": {}
                }
                
                span.update(
                    output=out_of_scope_response,
                    metadata={"route_type": "out_of_scope_llm"}
                )
                
                return out_of_scope_response
            
            # STEP 3: Process travel-related query with full LLM routing
            decision = llm_route(user_message, context)
            
            span.update(
                output=decision,
                metadata={
                    "route_type": "llm",
                    "actions_count": len(decision.get("actions", []))
                }
            )
            
            return decision
            
        except Exception as e:
            print(f"[ROUTER] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_response = {
                "reasoning": f"Error: {str(e)}",
                "actions": [],
                "message": "I'm having trouble. Could you try again?",
                "context_updates": {}
            }
            
            span.update(
                output=error_response,
                level="ERROR",
                status_message=str(e)
            )
            
            return error_response


def is_obviously_out_of_scope(message: str) -> bool:
    """
    Quick heuristic check for OBVIOUSLY out-of-scope queries.
    Only catches very clear cases to avoid false positives.
    """
    msg_lower = message.lower().strip()
    
    # Math operations (very obvious patterns only)
    math_patterns = [
        r'^\s*\d+\s*[\+\-\*\/×÷]\s*\d+\s*[=?]?\s*$',  # Just "4x2" or "2+2="
        r'^what\s+is\s+\d+\s*[\+\-\*\/×÷]\s*\d+',  # "what is 2+2"
        r'^calculate\s+\d+\s*[\+\-\*\/×÷]',  # "calculate 25+"
        r'^solve\s+\d+\s*[\+\-\*\/×÷]',  # "solve equation"
    ]
    
    for pattern in math_patterns:
        if re.search(pattern, msg_lower):
            print(f"[HEURISTIC] Math pattern detected: {pattern}")
            return True
    
    # Programming requests (very explicit only)
    explicit_code_phrases = [
        'write me a program',
        'write me a python program',
        'write me a javascript program',
        'write a function to',
        'write code to',
        'debug this code',
        'fix this code',
    ]
    
    for phrase in explicit_code_phrases:
        if phrase in msg_lower:
            print(f"[HEURISTIC] Code request detected: {phrase}")
            return True
    
    return False


def check_scope_with_llm(user_message: str) -> bool:
    """
    Use LLM to determine if query is travel-related.
    Uses caching for performance on similar queries.
    """
    with create_span("scope_check", input={"message": user_message}) as span:
        # Normalize message for cache key
        normalized = user_message.lower().strip()
        cache_key = hashlib.md5(normalized.encode()).hexdigest()
        
        # Check cache first
        if USE_SCOPE_CACHE and cache_key in SCOPE_CACHE:
            print(f"[SCOPE CHECK] Cache hit for: {user_message[:50]}...")
            cached_result = SCOPE_CACHE[cache_key]
            print(f"[SCOPE CHECK] Cached result: {'IN SCOPE' if cached_result else 'OUT OF SCOPE'}")
            
            span.update(
                output={"is_travel_related": cached_result, "source": "cache"},
                metadata={"cache_hit": True}
            )
            
            return cached_result
        
        print(f"[SCOPE CHECK] LLM check for: {user_message[:50]}...")
        
        # Build prompt
        prompt = f"""You are a travel assistant scope classifier. Determine if the user's query is about travel planning.

Travel-related topics include:
- Flights, hotels, accommodation
- Restaurants, food, dining
- Travel destinations, trip planning
- Travel dates, budgets, preferences
- Tourist attractions, activities

NOT travel-related:
- Math problems (2+2, 4x2, equations)
- Programming/coding requests
- General knowledge questions
- News, sports, entertainment
- Scientific questions

User query: {user_message}

Respond with ONLY this exact JSON format (no other text):
{{"is_travel_related": true, "reasoning": "brief explanation"}}

or

{{"is_travel_related": false, "reasoning": "brief explanation"}}

JSON only:"""

        try:
            raw_response = call_ollama(prompt, timeout=30)
            
            if not raw_response:
                print("[SCOPE CHECK] No response, defaulting to IN SCOPE")
                span.update(output={"is_travel_related": True, "source": "default"})
                return True  # Fail open
            
            print(f"[SCOPE CHECK] Raw response: {raw_response[:200]}")
            
            # Extract JSON
            scope_result = extract_json(raw_response)
            
            if not scope_result:
                print(f"[SCOPE CHECK] Failed to parse JSON, defaulting to IN SCOPE")
                span.update(output={"is_travel_related": True, "source": "parse_error"})
                return True  # Fail open
            
            is_travel = scope_result.get("is_travel_related", True)
            reasoning = scope_result.get("reasoning", "No reasoning")
            
            print(f"[SCOPE CHECK] Result: {'IN SCOPE' if is_travel else 'OUT OF SCOPE'}")
            print(f"[SCOPE CHECK] Reasoning: {reasoning}")
            
            # Cache the result
            cache_result(cache_key, is_travel)
            
            span.update(
                output={
                    "is_travel_related": is_travel,
                    "reasoning": reasoning,
                    "source": "llm"
                },
                metadata={"cache_hit": False}
            )
            
            return is_travel
            
        except Exception as e:
            print(f"[SCOPE CHECK] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            
            span.update(
                output={"is_travel_related": True, "source": "error"},
                level="ERROR",
                status_message=str(e)
            )
            
            return True  # Fail open


def cache_result(cache_key: str, result: bool):
    """Add result to cache, maintaining size limit."""
    if not USE_SCOPE_CACHE:
        return
    
    SCOPE_CACHE[cache_key] = result
    
    # Simple LRU: remove oldest if cache too large
    if len(SCOPE_CACHE) > MAX_CACHE_SIZE:
        oldest_key = next(iter(SCOPE_CACHE))
        del SCOPE_CACHE[oldest_key]


def llm_route(user_message: str, context: dict) -> dict:
    """
    Use LLM to route and reason about user requests.
    Only called for travel-related queries.
    """
    with create_span("llm_route", input={"message": user_message, "context": context}) as span:
        context_str = json.dumps(context, indent=2) if context else "{}"
        
        prompt = f"""{SYSTEM_PROMPT}

CURRENT CONTEXT:
{context_str}

USER MESSAGE:
{user_message}

Remember: Use single braces {{ }} not double braces {{{{ }}}}. Respond with ONLY valid JSON."""

        print(f"[LLM ROUTING] Processing: {user_message[:50]}...")
        
        try:
            raw_response = call_ollama(prompt)
            
            if not raw_response:
                print(f"[LLM ROUTING] Empty response")
                fallback = create_fallback_response()
                span.update(output=fallback, metadata={"fallback": "empty_response"})
                return fallback
            
            print(f"[LLM ROUTING] Response length: {len(raw_response)} chars")
            print(f"[LLM ROUTING] Raw response preview: {raw_response[:200]}...")
            
            # Check for double braces BEFORE parsing
            if '{{' in raw_response or '}}' in raw_response:
                print(f"[LLM ROUTING] ⚠️  Detected double braces in response, fixing...")
            
            decision = extract_json(raw_response)
            
            if not decision or not isinstance(decision, dict):
                print(f"[LLM ROUTING] ❌ JSON parse failed")
                print(f"[LLM ROUTING] Full raw response:")
                print(raw_response)
                print(f"[LLM ROUTING] End of raw response")
                
                fallback = create_fallback_response()
                span.update(output=fallback, metadata={"fallback": "parse_error", "raw": raw_response[:500]})
                return fallback
            
            print(f"[LLM ROUTING] ✅ Success: {decision.get('reasoning', 'N/A')[:50]}")
            
            # Ensure required fields
            decision.setdefault("reasoning", "")
            decision.setdefault("actions", [])
            decision.setdefault("message", "How can I help with your trip?")
            decision.setdefault("context_updates", {})
            
            # Convert old single-action format to multi-action
            if "action" in decision:
                if decision["action"] == "tool_call":
                    tool = decision.get("tool")
                    args = decision.get("args", {})
                    msg = decision.get("message", "")
                    
                    if tool:
                        decision["actions"] = [{
                            "tool": tool,
                            "args": args,
                            "message": msg
                        }]
                else:
                    decision["actions"] = []
                
                decision.pop("action", None)
                decision.pop("tool", None)
                decision.pop("args", None)
            
            span.update(output=decision)
            return decision
            
        except Exception as e:
            print(f"[LLM ROUTING] Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            
            fallback = create_fallback_response()
            span.update(
                output=fallback,
                level="ERROR",
                status_message=str(e)
            )
            return fallback


def create_fallback_response() -> dict:
    """Create a safe fallback response."""
    return {
        "reasoning": "Failed to parse LLM response",
        "actions": [],
        "message": "Could you rephrase that? I'm here to help with flights, hotels, and restaurants.",
        "context_updates": {}
    }


def extract_json(text: str) -> dict:
    """
    Aggressively extract JSON from text with multiple strategies.
    Handles common LLM quirks like double braces, incomplete JSON, etc.
    """
    if not text:
        return None
    
    text = text.strip()
    
    # Strategy 0: Fix double braces (common LLM mistake)
    # Replace {{ with { and }} with } but be careful with nested objects
    text = re.sub(r'\{\{', '{', text)
    text = re.sub(r'\}\}', '}', text)
    
    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Remove markdown code blocks
    if '```' in text:
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Extract JSON object (ignore surrounding text)
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
        json_candidate = text[first_brace:last_brace+1]
        
        # Try to fix incomplete JSON
        json_candidate = fix_incomplete_json(json_candidate)
        
        try:
            parsed = json.loads(json_candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: Find all JSON-like structures
    # Look for { ... } patterns
    json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    
    for match in sorted(matches, key=len, reverse=True):
        match = fix_incomplete_json(match)
        try:
            parsed = json.loads(match)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    
    return None


def fix_incomplete_json(json_str: str) -> str:
    """
    Try to fix common JSON issues in LLM responses.
    """
    # Remove trailing commas before closing braces/brackets
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # If JSON is incomplete (cut off), try to complete it
    # Count braces and brackets
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    open_brackets = json_str.count('[')
    close_brackets = json_str.count(']')
    
    # Add missing closing braces
    if open_braces > close_braces:
        json_str += '}' * (open_braces - close_braces)
    
    # Add missing closing brackets
    if open_brackets > close_brackets:
        json_str += ']' * (open_brackets - close_brackets)
    
    return json_str