#!/usr/bin/env python3
"""Prompt Tester - Test different prompts quickly"""

import asyncio
import aiohttp
import json
import uuid
import argparse
from datetime import datetime
from pathlib import Path

class PromptTester:
    def __init__(self, llm_endpoint="http://127.0.0.1:1234/v1/chat/completions"):
        self.llm_endpoint = llm_endpoint
        
    async def test_prompt(self, prompt, model_name="auto", temperature=0.9, max_tokens=2000):
        """Test a single prompt"""
        start_time = datetime.now()
        
        # Auto-detect model if needed
        if model_name == "auto":
            model_name = await self.get_available_model()
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.llm_endpoint, json=payload, timeout=60) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        end_time = datetime.now()
                        duration_ms = int((end_time - start_time).total_seconds() * 1000)
                        
                        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        usage = data.get("usage", {})
                        completion_tokens = usage.get("completion_tokens", len(text.split()))
                        tokens_per_sec = completion_tokens / (duration_ms / 1000) if duration_ms > 0 else 0
                        
                        return {
                            "success": True,
                            "text": text,
                            "model": model_name,
                            "duration_ms": duration_ms,
                            "tokens": completion_tokens,
                            "tokens_per_sec": tokens_per_sec,
                            "chars": len(text)
                        }
                    else:
                        error_text = await resp.text()
                        return {"success": False, "error": f"HTTP {resp.status}: {error_text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_available_model(self):
        """Get first available model"""
        try:
            async with aiohttp.ClientSession() as session:
                models_url = self.llm_endpoint.replace('/chat/completions', '/models')
                async with session.get(models_url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["id"] for m in data.get("data", [])]
                        # Filter out embedding models
                        chat_models = [m for m in models if not any(x in m.lower() for x in ['embed', 'embedding'])]
                        return chat_models[0] if chat_models else "unknown"
        except:
            pass
        return "unknown"
    
    def format_conversation(self, text):
        """Convert raw text to structured format and count turns"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        turns = []
        
        for line in lines:
            if line.startswith("User:"):
                turns.append(("User", line[5:].strip()))
            elif line.startswith("Agent:"):
                turns.append(("Agent", line[6:].strip()))
        
        return {
            "turns": turns,
            "turn_count": len(turns),
            "complete": len(turns) >= 4  # Basic completeness check
        }
    
    def save_result(self, result, output_file):
        """Save result to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory
        output_dir = Path("prompt_tests")
        output_dir.mkdir(exist_ok=True)
        
        # Save detailed result
        filename = output_dir / f"{output_file}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        
        return filename

async def main():
    parser = argparse.ArgumentParser(description="Test LLM prompts")
    parser.add_argument("--prompt", required=True, help="Prompt to test")
    parser.add_argument("--model", default="auto", help="Model name (auto-detect if not specified)")
    parser.add_argument("--count", type=int, default=1, help="Number of tests to run")
    parser.add_argument("--output", default="test", help="Output file prefix")
    parser.add_argument("--endpoint", default="http://127.0.0.1:1234/v1/chat/completions", help="LLM endpoint")
    
    args = parser.parse_args()
    
    tester = PromptTester(args.endpoint)
    
    print(f"Testing prompt {args.count} times...")
    print(f"Endpoint: {args.endpoint}")
    print(f"Model: {args.model}")
    print("-" * 60)
    
    results = []
    
    for i in range(args.count):
        print(f"\nTest {i+1}/{args.count}:")
        
        result = await tester.test_prompt(args.prompt, args.model)
        
        if result["success"]:
            # Parse conversation
            conversation = tester.format_conversation(result["text"])
            
            # Add conversation analysis to result
            result["conversation"] = conversation
            
            # Print summary
            print(f"Success: {result['chars']} chars, {conversation['turn_count']} turns, {result['tokens_per_sec']:.1f} tok/s")
            print(f"  Complete: {conversation['complete']}")
            print(f"  First turn: {conversation['turns'][0][1][:50]}..." if conversation['turns'] else "  No turns found")
            
            # Save to file
            filename = tester.save_result(result, f"{args.output}_{i+1}")
            print(f"  Saved: {filename}")
            
        else:
            print(f"Failed: {result['error']}")
        
        results.append(result)
    
    # Summary
    successful = [r for r in results if r["success"]]
    if successful:
        avg_turns = sum(r["conversation"]["turn_count"] for r in successful) / len(successful)
        avg_speed = sum(r["tokens_per_sec"] for r in successful) / len(successful)
        complete_count = sum(1 for r in successful if r["conversation"]["complete"])
        
        print(f"\n" + "="*60)
        print(f"SUMMARY ({len(successful)}/{len(results)} successful):")
        print(f"Average turns: {avg_turns:.1f}")
        print(f"Average speed: {avg_speed:.1f} tok/s")
        print(f"Complete conversations: {complete_count}/{len(successful)}")

if __name__ == "__main__":
    asyncio.run(main())