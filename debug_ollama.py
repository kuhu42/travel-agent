#!/usr/bin/env python3
"""
Test script for Langfuse context manager integration.
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("LANGFUSE CONTEXT MANAGER TEST")
print("=" * 60)
print()

# Test 1: Check environment
print("Step 1: Checking environment...")
public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
secret_key = os.getenv("LANGFUSE_SECRET_KEY")

if public_key and secret_key:
    print(f"✅ API keys found")
    print(f"   Public key: {public_key[:15]}...")
    print(f"   Secret key: {secret_key[:15]}...")
else:
    print("⚠️  API keys not found in .env")
print()

# Test 2: Import Langfuse
print("Step 2: Testing Langfuse import...")
try:
    from langfuse import get_client
    print("✅ Successfully imported get_client")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Run: pip install 'langfuse>=2.0.0'")
    exit(1)
print()

# Test 3: Import your config
print("Step 3: Testing langfuse_config...")
try:
    from langfuse_config import (
        LANGFUSE_ENABLED,
        create_span,
        create_generation,
        flush,
        langfuse
    )
    print("✅ Successfully imported langfuse_config")
    print(f"   Langfuse enabled: {LANGFUSE_ENABLED}")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    exit(1)
print()

# Test 4: Test context managers
print("Step 4: Testing context managers...")

# Test span
print("  Testing create_span()...")
with create_span("test-span", input={"test": "data"}) as span:
    span.update(output={"result": "success"})
    print("  ✅ Span context manager works")

# Test generation
print("  Testing create_generation()...")
with create_generation("test-generation", model="test-model") as gen:
    gen.update(
        input={"prompt": "hello"},
        output={"response": "hi"},
        usage={"tokens": 10}
    )
    print("  ✅ Generation context manager works")

# Test nested spans
print("  Testing nested spans...")
with create_span("parent-span") as parent:
    parent.update(input={"operation": "parent"})
    
    with create_span("child-span") as child:
        child.update(input={"operation": "child"})
        child.update(output={"status": "complete"})
    
    parent.update(output={"status": "complete"})
    print("  ✅ Nested spans work")

print()

# Test 5: Test your actual modules
print("Step 5: Testing your modules...")

try:
    from agent.router import route
    print("✅ router.py imported successfully")
    
    # Test a simple route
    print("\n  Running test route...")
    result = route("I want to go to Paris", {})
    print(f"  ✅ Route executed: {result.get('message', 'N/A')[:50]}...")
    
except Exception as e:
    print(f"❌ router.py test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 6: Flush events
print("Step 6: Flushing events to Langfuse...")
flush()
print("✅ Events flushed")
print()

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)

if LANGFUSE_ENABLED:
    print("✅ Langfuse integration working with context managers!")
    print()
    print("What you should see in Langfuse dashboard:")
    print("  1. Go to your Langfuse dashboard")
    print("  2. Navigate to 'Tracing' section")
    print("  3. Look for traces with names like:")
    print("     - test-span")
    print("     - test-generation")
    print("     - parent-span (with nested child-span)")
    print("     - router (from your actual code)")
    print()
    print("Each trace will show:")
    print("  - Input/output data")
    print("  - Execution time")
    print("  - Nested operations")
    print("  - Usage metrics (for generations)")
else:
    print("⚠️  Langfuse is disabled")
    print("   The code works but no data is sent to Langfuse")
    print()
    print("To enable:")
    print("  1. Set API keys in .env")
    print("  2. Restart your application")

print("=" * 60)