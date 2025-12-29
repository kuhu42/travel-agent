"""
Langfuse configuration and initialization.
Uses the modern context manager API.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if Langfuse is configured
LANGFUSE_ENABLED = bool(
    os.getenv("LANGFUSE_PUBLIC_KEY") and 
    os.getenv("LANGFUSE_SECRET_KEY")
)

if LANGFUSE_ENABLED:
    try:
        from langfuse import get_client
        
        # Initialize Langfuse client using get_client()
        langfuse = get_client()
        
        print("✅ Langfuse logging enabled")
        print(f"   Host: {os.getenv('LANGFUSE_HOST', os.getenv('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com'))}")
        
    except ImportError as e:
        print(f"⚠️  Langfuse import error: {e}")
        print(f"   Install with: pip install 'langfuse>=2.0.0'")
        LANGFUSE_ENABLED = False
        langfuse = None
        
    except Exception as e:
        print(f"⚠️  Langfuse initialization error: {e}")
        print(f"   Check your API keys in .env")
        LANGFUSE_ENABLED = False
        langfuse = None
        
else:
    print("⚠️  Langfuse not configured - logging disabled")
    print("   Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env")
    langfuse = None


def get_langfuse_client():
    """Get Langfuse client instance."""
    return langfuse if LANGFUSE_ENABLED else None


class NoOpSpan:
    """Dummy span when Langfuse is disabled."""
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def update(self, **kwargs):
        pass
    
    def generation(self, **kwargs):
        return NoOpSpan()
    
    def span(self, **kwargs):
        return NoOpSpan()
    
    def event(self, **kwargs):
        pass


def create_span(name: str, **kwargs):
    """
    Create a Langfuse span using context manager.
    Returns a no-op span if Langfuse is disabled.
    
    Usage:
        with create_span("my-operation") as span:
            # Your code here
            span.update(output="result")
    """
    if LANGFUSE_ENABLED and langfuse:
        return langfuse.start_as_current_observation(
            as_type="span",
            name=name,
            **kwargs
        )
    else:
        return NoOpSpan()


def create_generation(name: str, model: str = None, **kwargs):
    """
    Create a Langfuse generation (for LLM calls) using context manager.
    Returns a no-op span if Langfuse is disabled.
    
    Usage:
        with create_generation("llm-call", model="llama3.2:3b") as gen:
            # Your LLM call
            gen.update(
                input="prompt",
                output="response",
                usage={"tokens": 100}
            )
    """
    if LANGFUSE_ENABLED and langfuse:
        kwargs_with_model = {"as_type": "generation", "name": name, **kwargs}
        if model:
            kwargs_with_model["model"] = model
        return langfuse.start_as_current_observation(**kwargs_with_model)
    else:
        return NoOpSpan()


def flush():
    """Flush events to Langfuse. Call at the end of your application."""
    if LANGFUSE_ENABLED and langfuse:
        langfuse.flush()


__all__ = [
    'langfuse',
    'LANGFUSE_ENABLED',
    'get_langfuse_client',
    'create_span',
    'create_generation',
    'flush',
    'NoOpSpan'
]