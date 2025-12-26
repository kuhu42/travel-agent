import json
import yaml
import re
from llm.ollama_client import call_ollama

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

SYSTEM_PROMPT = config["agent"]["system_prompt"]
ENABLE_FAST_ROUTING = True

def route(user_message: str, context: dict) -> dict:
    """
    Enhanced routing that can detect MULTIPLE tool requests.
    """
    
    # FAST PATH: Check for obvious patterns
    if ENABLE_FAST_ROUTING:
        fast_result = fast_route_multi(user_message, context)
        if fast_result:
            return fast_result
    
    # SLOW PATH: Use LLM for complex queries
    return llm_route_multi(user_message, context)


def fast_route_multi(user_message: str, context: dict) -> dict:
    """
    Fast keyword-based routing that detects MULTIPLE requests.
    IMPROVED: Only clarify if CRITICAL info is missing.
    """
    msg_lower = user_message.lower()
    
    # Extract entities
    extracted = extract_entities(user_message, context)
    dest = extracted.get('destination') or context.get('destination')
    dates = extracted.get('dates') or context.get('dates')
    budget = extracted.get('budget') or context.get('budget')
    
    actions = []
    
    # Check for FLIGHT request
    if any(word in msg_lower for word in ['flight', 'fly', 'ticket', 'airline', 'book']):
        # ONLY require destination AND dates (budget is optional!)
        if dest and dates:
            # Extract any filters from the message
            filters = extract_filters(msg_lower)
            
            actions.append({
                "tool": "search_flights",
                "args": {
                    "destination": dest, 
                    "dates": dates, 
                    "budget": budget,
                    "filters": filters  # Pass along filters like "cheapest", "1 stop"
                },
                "message": f"Searching flights to {dest} for {dates}..."
            })
        elif not dest and not dates:
            # Missing BOTH critical pieces
            return {
                "reasoning": "Need both destination and dates for flights",
                "actions": [],
                "message": "I'd love to find flights! I need to know where you're going and when.",
                "context_updates": extracted
            }
        elif not dest:
            # Only missing destination
            return {
                "reasoning": "Need destination for flights",
                "actions": [],
                "message": f"I can find flights for {dates}! Which city are you flying to?",
                "context_updates": extracted
            }
        else:
            # Only missing dates
            return {
                "reasoning": "Need dates for flights",
                "actions": [],
                "message": f"I can find flights to {dest}! When are you planning to travel?",
                "context_updates": extracted
            }
    
    # Check for HOTEL request
    if any(word in msg_lower for word in ['hotel', 'stay', 'accommodation', 'room', 'lodge']):
        if dest:
            actions.append({
                "tool": "search_hotels",
                "args": {"destination": dest, "budget": budget, "dates": dates},
                "message": f"Searching hotels in {dest}..."
            })
        else:
            # Only ask for clarification if NO destination at all
            return {
                "reasoning": "Need destination for hotels",
                "actions": [],
                "message": "I can find hotels! Which city are you looking at?",
                "context_updates": extracted
            }
    
    # Check for FOOD request
    if any(word in msg_lower for word in ['food', 'restaurant', 'eat', 'dining', 'cafe']):
        if dest:
            preference = None
            if 'vegetarian' in msg_lower or 'vegan' in msg_lower:
                preference = 'vegetarian'
            elif 'fine dining' in msg_lower or 'fancy' in msg_lower:
                preference = 'fine dining'
            elif 'cheap' in msg_lower or 'budget' in msg_lower:
                preference = 'budget'
            
            actions.append({
                "tool": "recommend_food",
                "args": {"destination": dest, "preference": preference},
                "message": f"Finding restaurants in {dest}..."
            })
        else:
            return {
                "reasoning": "Need destination for food",
                "actions": [],
                "message": "I can recommend restaurants! Which city?",
                "context_updates": extracted
            }
    
    # If we found actions, return them
    if actions:
        return {
            "reasoning": f"Fast route: Detected {len(actions)} request(s). Proceeding with available context.",
            "actions": actions,
            "context_updates": extracted
        }
    
    # Greetings or simple responses
    if any(word in msg_lower for word in ['hi', 'hello', 'hey', 'thanks', 'thank you']):
        return {
            "reasoning": "Greeting",
            "actions": [],
            "message": "Hello! I can help you find flights, hotels, and restaurants. What are you planning?",
            "context_updates": {}
        }
    
    # No match - use LLM
    return None


def extract_filters(msg_lower: str) -> dict:
    """
    Extract filtering criteria from the message.
    Examples: "cheapest", "1 stop", "direct flight", "fastest"
    """
    filters = {}
    
    # Price-related
    if 'cheapest' in msg_lower or 'cheap' in msg_lower or 'budget' in msg_lower:
        filters['price_preference'] = 'cheapest'
    elif 'expensive' in msg_lower or 'premium' in msg_lower or 'luxury' in msg_lower:
        filters['price_preference'] = 'expensive'
    
    # Stops
    if 'direct' in msg_lower or 'non-stop' in msg_lower or 'nonstop' in msg_lower or '0 stop' in msg_lower:
        filters['max_stops'] = 0
    elif '1 stop' in msg_lower or 'one stop' in msg_lower:
        filters['max_stops'] = 1
    elif '2 stop' in msg_lower or 'two stop' in msg_lower:
        filters['max_stops'] = 2
    
    # Duration
    if 'fastest' in msg_lower or 'quickest' in msg_lower or 'shortest' in msg_lower:
        filters['duration_preference'] = 'shortest'
    
    return filters


def extract_entities(message: str, context: dict) -> dict:
    """
    Quick entity extraction using regex patterns.
    """
    updates = {}
    msg_lower = message.lower()
    
    # Extract destination
    cities = ['paris', 'london', 'tokyo', 'dubai', 'new york', 'singapore', 
              'barcelona', 'rome', 'bangkok', 'istanbul', 'amsterdam', 'berlin',
              'madrid', 'sydney', 'mumbai', 'delhi', 'bangalore', 'goa']
    
    for city in cities:
        if city in msg_lower:
            updates['destination'] = city.title()
            break
    
    # Extract dates with more patterns
    date_patterns = [
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}[-–to ]+\d{1,2}',
        r'\d{1,2}[-–to ]+\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*',
        r'\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            updates['dates'] = match.group(0).strip()
            break
    
    # Extract budget
    budget_match = re.search(r'(?:under|below|max|budget)\s+(\d+)', msg_lower)
    if budget_match:
        updates['budget'] = budget_match.group(1)
    
    return updates


def llm_route_multi(user_message: str, context: dict) -> dict:
    """
    LLM-based routing for complex queries.
    """
    context_str = json.dumps(context, indent=2)
    
    prompt = f"""{SYSTEM_PROMPT}

Context: {context_str}
User: {user_message}

IMPORTANT: Only ask for clarification if CRITICAL information is missing.
- For flights: MUST have destination AND dates
- For hotels: MUST have destination
- For food: MUST have destination
Budget and preferences are OPTIONAL - proceed without them if not provided.

Return JSON with actions array:"""

    raw = call_ollama(prompt)
    decision = extract_json(raw)
    
    if not decision or not isinstance(decision, dict):
        return {
            "reasoning": "LLM parsing failed",
            "actions": [],
            "message": "I'm having trouble understanding. Could you rephrase?",
            "context_updates": {}
        }
    
    # Ensure proper structure
    decision.setdefault("reasoning", "LLM route")
    decision.setdefault("actions", [])
    decision.setdefault("context_updates", {})
    
    # Handle old single-action format for backward compatibility
    if "action" in decision and decision.get("action") == "tool_call":
        decision["actions"] = [{
            "tool": decision.get("tool"),
            "args": decision.get("args", {}),
            "message": decision.get("message", "")
        }]
    
    if not decision.get("actions"):
        decision.setdefault("message", "How can I help with your travel plans?")
    
    return decision


def extract_json(text: str) -> dict:
    """Extract JSON from text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try markdown blocks
    json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_block_pattern, text, re.DOTALL)
    if matches:
        try:
            return json.loads(matches[0])
        except json.JSONDecodeError:
            pass
    
    # Try any JSON object
    json_pattern = r'\{(?:[^{}]|\{[^{}]*\})*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    for match in reversed(matches):
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None