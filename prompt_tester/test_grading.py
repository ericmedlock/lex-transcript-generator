#!/usr/bin/env python3
"""
Test OpenAI grading directly
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

def test_grading():
    print("Testing OpenAI grading...")
    
    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"API Key loaded: {api_key[:20]}...")
    
    # Initialize client
    client = OpenAI(api_key=api_key)
    
    # Test conversation
    test_conversation = """User: Hi, I need to see a doctor today.
Agent: Good morning! Can I get your name please?
User: It's John Smith. I have a bad cough.
Agent: Thank you Mr. Smith. Let me check availability."""
    
    # Grade it
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Rate this healthcare conversation 1-10 for realness: {test_conversation}"}],
            temperature=0.1,
            max_tokens=50
        )
        
        result = response.choices[0].message.content
        print(f"Grading result: {result}")
        print("SUCCESS: OpenAI grading works!")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_grading()