import requests
import yaml

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = config["llm"]["model"]

def call_ollama(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    return response.json()["response"]
