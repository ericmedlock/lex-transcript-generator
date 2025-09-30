#!/usr/bin/env python3
"""
Test script for AI_Catalyst LLM provider
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_catalyst.llm import LLMProvider, EndpointDiscovery


def test_endpoint_discovery():
    """Test endpoint discovery"""
    print("=== Testing Endpoint Discovery ===")
    
    endpoints = EndpointDiscovery.discover_local_endpoints()
    print(f"Discovered local endpoints: {endpoints}")
    
    for endpoint in endpoints:
        info = EndpointDiscovery.get_endpoint_info(endpoint)
        print(f"Endpoint {endpoint}:")
        print(f"  Available: {info['available']}")
        print(f"  Models: {info['models'][:3]}...")  # Show first 3 models
        if info['error']:
            print(f"  Error: {info['error']}")


def test_llm_provider():
    """Test LLM provider"""
    print("\n=== Testing LLM Provider ===")
    
    # Initialize provider
    provider = LLMProvider()
    
    # Check available providers
    available = provider.get_available_providers()
    print(f"Available providers: {available}")
    
    # Test simple generation with auto provider
    if available:
        print("\nTesting generation with auto provider...")
        result = provider.generate(
            "Say 'Hello from AI_Catalyst!' and nothing else.",
            provider="auto",
            temperature=0.1,
            max_tokens=50
        )
        
        print(f"Provider used: {result['provider_used']}")
        print(f"Content: {result['content']}")
        if result['error']:
            print(f"Error: {result['error']}")
    else:
        print("No providers available for testing")


def main():
    """Run tests"""
    print("AI_Catalyst LLM Provider Test")
    print("=" * 40)
    
    try:
        test_endpoint_discovery()
        test_llm_provider()
        print("\n[SUCCESS] Tests completed successfully")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()