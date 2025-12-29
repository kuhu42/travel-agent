import json
import yaml
import re
from llm.ollama_client import call_ollama

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

SYSTEM_PROMPT = config["agent"]["system_prompt"]

def route(user_message: str, context: dict) -> dict:
    """
    Enhanced routing with better context awareness and reasoning.
    """
    # Build a comprehensive prompt with context
    context_str = json.dumps(context, indent=2)
    
    prompt = f"""
{SYSTEM_PROMPT}

CURRENT CONTEXT:
{context_str}

USER MESSAGE:
{user_message}

Analyze the user's message considering the current context, then respond with your decision in valid JSON format.
Remember to extract any new information (destination, dates, budget, preferences) and include it in context_updates.
"""

    raw = call_ollama(prompt)
    
    # Try to extract JSON from the response
    decision = extract_json(raw)
    
    # Validate and provide defaults
    if not decision or not isinstance(decision, dict):
        return {
            "reasoning": "Failed to parse LLM response",
            "action": "respond",
            "message": "I'm having trouble understanding. Could you rephrase that?",
            "context_updates": {}
        }
    
    # Ensure required fields exist
    decision.setdefault("reasoning", "")
    decision.setdefault("action", "respond")
    decision.setdefault("message", "How can I assist you with your travel plans?")
    decision.setdefault("context_updates", {})
    
    return decision


def extract_json(text: str) -> dict:
    """
    Extract JSON from text that might contain markdown code blocks or other text.
    """
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON in markdown code blocks
    json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_block_pattern, text, re.DOTALL)
    if matches:
        try:
            return json.loads(matches[0])
        except json.JSONDecodeError:
            pass
    
    # Try to find any JSON object in the text
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None