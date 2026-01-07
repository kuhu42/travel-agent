"""
Simplified Langfuse configuration with context managers.
"""

import os
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

LANGFUSE_ENABLED = bool(
    os.getenv("LANGFUSE_PUBLIC_KEY") and 
    os.getenv("LANGFUSE_SECRET_KEY")
)

if LANGFUSE_ENABLED:
    try:
        from langfuse import Langfuse
        
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        )
        
        print("✅ Langfuse logging enabled")
        
    except ImportError:
        print("⚠️  Langfuse package not installed")
        LANGFUSE_ENABLED = False
        langfuse = None
        
else:
    print("⚠️  Langfuse not configured")
    langfuse = None


# Context managers for easy usage
@contextmanager
def create_span(name, input=None, metadata=None):
    """Context manager for creating spans."""
    class DummySpan:
        def update(self, **kwargs):
            pass
    
    if LANGFUSE_ENABLED and langfuse:
        try:
            span = langfuse.span(name=name, input=input, metadata=metadata)
            yield span
            span.end()
        except:
            yield DummySpan()
    else:
        yield DummySpan()


@contextmanager
def create_generation(name, model=None, input=None, metadata=None):
    """Context manager for creating generations."""
    class DummyGeneration:
        def update(self, **kwargs):
            pass
    
    if LANGFUSE_ENABLED and langfuse:
        try:
            gen = langfuse.generation(
                name=name,
                model=model,
                input=input,
                metadata=metadata
            )
            yield gen
            gen.end()
        except:
            yield DummyGeneration()
    else:
        yield DummyGeneration()


def flush():
    """Flush pending events."""
    if LANGFUSE_ENABLED and langfuse:
        try:
            langfuse.flush()
        except:
            pass


__all__ = [
    'LANGFUSE_ENABLED',
    'langfuse',
    'create_span',
    'create_generation',
    'flush'
]