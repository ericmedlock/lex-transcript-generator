#!/usr/bin/env python3
"""Test OpenAI API key"""

import os
from openai import OpenAI

# Load from environment
api_key = os.getenv('OPENAI_API_KEY')
print(f"API Key from env: {api_key[:20]}...{api_key[-10:] if api_key else 'None'}")

# Test connection
if api_key:
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5
        )
        print("✓ OpenAI API key is working")
    except Exception as e:
        print(f"✗ OpenAI API error: {e}")
else:
    print("✗ No API key found")