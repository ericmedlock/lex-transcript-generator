#!/usr/bin/env python3
"""
Integration test - Verify AI_Catalyst can be used by existing code
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_catalyst.llm import LLMProvider


def test_conversation_grading_integration():
    """Test that AI_Catalyst can handle conversation grading tasks"""
    print("=== Testing Conversation Grading Integration ===")
    
    # Initialize provider
    provider = LLMProvider()
    
    # Sample conversation for grading
    sample_conversation = """
    Patient: Hi, I'd like to schedule an appointment with Dr. Smith.
    Receptionist: Of course! What type of appointment are you looking for?
    Patient: I need a follow-up for my blood pressure medication.
    Receptionist: I have an opening next Tuesday at 2 PM. Does that work?
    Patient: Perfect, thank you!
    """
    
    # Create a grading prompt similar to what conversation_grader.py uses
    grading_prompt = f"""Grade this AI-generated conversation on a scale of 1-10 for each metric:

1. REALNESS: How realistic and believable is this conversation? (1=obviously AI, 10=indistinguishable from human)
2. COHERENCE: How well does the conversation flow logically? (1=nonsensical, 10=perfect flow)
3. NATURALNESS: How natural do the speech patterns sound? (1=robotic, 10=completely natural)
4. OVERALL: Overall quality for training chatbot systems (1=unusable, 10=excellent training data)
5. HEALTHCARE_VALID: Is this actually a healthcare appointment conversation? (true/false)

Conversation to grade:
{sample_conversation}

Respond ONLY with JSON format:
{{
  "realness_score": X,
  "coherence_score": X,
  "naturalness_score": X,
  "overall_score": X,
  "healthcare_valid": true/false,
  "brief_feedback": "one sentence explanation"
}}"""
    
    # Test with local provider
    print("Testing with local provider...")
    result = provider.generate(
        grading_prompt,
        provider="local",
        temperature=0.1,
        max_tokens=200
    )
    
    print(f"Provider used: {result['provider_used']}")
    if result['error']:
        print(f"Error: {result['error']}")
    else:
        print("Response received:")
        print(result['content'][:200] + "..." if len(result['content']) > 200 else result['content'])
        
        # Try to parse as JSON to verify format
        try:
            import json
            # Clean response like conversation_grader.py does
            content = result['content'].strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            grades = json.loads(content)
            print("✓ Successfully parsed JSON response")
            print(f"  Realness: {grades.get('realness_score')}")
            print(f"  Healthcare Valid: {grades.get('healthcare_valid')}")
        except json.JSONDecodeError as e:
            print(f"⚠ JSON parsing failed: {e}")


def main():
    """Run integration tests"""
    print("AI_Catalyst Integration Test")
    print("=" * 40)
    
    try:
        test_conversation_grading_integration()
        print("\n[SUCCESS] Integration tests completed")
    except Exception as e:
        print(f"\n[ERROR] Integration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()