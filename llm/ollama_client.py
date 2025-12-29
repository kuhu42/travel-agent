import requests
import yaml
from langfuse_config import LANGFUSE_ENABLED, create_generation

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = config["llm"]["model"]
TEMPERATURE = config["llm"].get("temperature", 0.7)
MAX_TOKENS = config["llm"].get("max_tokens", 500)
TIMEOUT = 60


def call_ollama(prompt: str, timeout: int = TIMEOUT) -> str:
    """
    Call Ollama API with Langfuse generation tracking using context manager.
    Returns empty string on error instead of raising exception.
    """
    with create_generation(
        name="ollama_call",
        model=MODEL,
        input=prompt,
        metadata={
            "provider": "ollama",
            "endpoint": OLLAMA_URL,
            "timeout": timeout,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS
        }
    ) as generation:
        
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": TEMPERATURE,
                "num_predict": MAX_TOKENS,
                "num_thread": 4,
                "num_ctx": 2048,
                "num_batch": 512,
            }
        }

        try:
            print(f"[OLLAMA] Calling {MODEL} (timeout: {timeout}s, max_tokens: {MAX_TOKENS})...")
            
            response = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
            response.raise_for_status()
            result = response.json()
            
            if "response" not in result:
                print(f"[OLLAMA] Unexpected response format: {result}")
                generation.update(
                    output="",
                    level="ERROR",
                    status_message="Unexpected response format"
                )
                return ""
            
            output = result["response"]
            
            # Log performance metrics if available
            usage_data = {}
            if "eval_count" in result:
                eval_count = result["eval_count"]
                prompt_eval_count = result.get("prompt_eval_count", 0)
                eval_duration = result.get("eval_duration", 0) / 1e9  # nanoseconds to seconds
                
                usage_data = {
                    "input": prompt_eval_count,
                    "output": eval_count,
                    "total": prompt_eval_count + eval_count
                }
                
                if eval_duration > 0:
                    tokens_per_sec = eval_count / eval_duration
                    print(f"[OLLAMA] Generated {eval_count} tokens in {eval_duration:.1f}s ({tokens_per_sec:.1f} tok/s)")
                    
                    # Warn if very slow
                    if tokens_per_sec < 5:
                        print(f"[OLLAMA] ⚠️  Very slow generation. Consider using llama3.2:3b or llama3.2:1b")
            
            # Update generation with output and usage
            generation.update(
                output=output,
                usage=usage_data if usage_data else None
            )
            
            return output
            
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to Ollama. Is it running? (ollama serve)"
            print(f"[OLLAMA] ERROR: {error_msg}")
            
            generation.update(
                output="",
                level="ERROR",
                status_message=error_msg
            )
            
            return ""
            
        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after {timeout}s. Model is too slow - switch to llama3.2:3b"
            print(f"[OLLAMA] ERROR: {error_msg}")
            print(f"[OLLAMA] Quick fix: ollama pull llama3.2:3b")
            
            generation.update(
                output="",
                level="ERROR",
                status_message=error_msg
            )
            
            return ""
            
        except Exception as e:
            error_msg = f"Ollama error: {str(e)}"
            print(f"[OLLAMA] ERROR: {error_msg}")
            
            generation.update(
                output="",
                level="ERROR",
                status_message=error_msg
            )
            
            return ""