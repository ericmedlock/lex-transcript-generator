#!/usr/bin/env python3
"""
Prompt Tester - Test conversational models with healthcare appointment prompts
"""

import yaml
import time
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.discovery.model_discovery import ModelDiscovery
from src.testing.prompt_executor import PromptExecutor
from src.monitoring.resource_monitor import ResourceMonitor
from src.scoring.quality_scorer import QualityScorer
from src.reporting.csv_reporter import CSVReporter

class PromptTester:
    def __init__(self):
        self.model_discovery = ModelDiscovery()
        self.prompt_executor = PromptExecutor()
        self.resource_monitor = ResourceMonitor()
        self.quality_scorer = QualityScorer()
        self.csv_reporter = CSVReporter()
        
        # Load test prompts
        with open("config/test_prompts.yaml", "r") as f:
            self.prompts_config = yaml.safe_load(f)
    
    def run_tests(self) -> str:
        """Run complete test suite and return CSV report path"""
        print("=== Prompt Tester Starting ===")
        
        # Discover models
        print("Discovering conversational models...")
        models = self.model_discovery.discover_conversational_models()
        
        if not models:
            print("No conversational models found in LM Studio")
            return None
        
        print(f"Found {len(models)} conversational models:")
        for model in models:
            print(f"  - {model['id']}")
        
        # Test each model with each prompt
        test_results = []
        
        for model in models:
            model_id = model["id"]
            print(f"\nTesting model: {model_id}")
            
            # Test model availability
            if not self.model_discovery.test_model_availability(model_id):
                print(f"  Model {model_id} not responsive, skipping...")
                continue
            
            for prompt_config in self.prompts_config["healthcare_appointment_prompts"]:
                prompt_id = prompt_config["id"]
                prompt_text = prompt_config["prompt"]
                
                # Run 3 rounds per prompt
                for round_num in range(1, 4):
                    print(f"  Running prompt: {prompt_id} (Round {round_num}/3)")
                    
                    # Start resource monitoring
                    self.resource_monitor.start_monitoring()
                    
                    # Execute prompt
                    conversation, performance_metrics = self.prompt_executor.execute_prompt(
                        model_id, prompt_text
                    )
                    
                    # Stop resource monitoring
                    resource_metrics = self.resource_monitor.stop_monitoring()
                    
                    if performance_metrics["success"]:
                        print(f"    Generated {performance_metrics['completion_tokens']} tokens in {performance_metrics['total_time']:.2f}s")
                        print(f"    Speed: {performance_metrics['tokens_per_second']:.2f} tokens/sec")
                        
                        # Score quality
                        print("    Scoring quality...")
                        quality_scores = self.quality_scorer.score_conversation(conversation, prompt_text)
                        
                        if quality_scores.get("grading_error"):
                            print(f"    Grading error: {quality_scores['grading_error']}")
                        else:
                            print(f"    Quality: R={quality_scores.get('realness_score')}, O={quality_scores.get('overall_score')}")
                    else:
                        print(f"    Execution failed: {performance_metrics['error']}")
                        quality_scores = {}
                    
                    # Store results
                    test_results.append({
                        "model_id": model_id,
                        "prompt_id": f"{prompt_id}_round_{round_num}",
                        "prompt_text": prompt_text,
                        "generated_conversation": conversation,
                        "grading_prompt": self._build_grading_prompt(conversation, prompt_text),
                        "performance_metrics": performance_metrics,
                        "resource_metrics": resource_metrics,
                        "quality_scores": quality_scores,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Brief pause between rounds
                    time.sleep(2)
        
        # Generate CSV report
        print(f"\nGenerating CSV report...")
        report_path = self.csv_reporter.generate_report(test_results)
        
        print(f"=== Testing Complete ===")
        print(f"Tested {len([r for r in test_results if r['performance_metrics']['success']])} successful prompts")
        print(f"Report saved to: {report_path}")
        
        return report_path
    
    def _build_grading_prompt(self, conversation: str, original_prompt: str) -> str:
        """Build the grading prompt for reference"""
        return f"""Grade this AI-generated healthcare appointment conversation on a scale of 1-10 for each metric:

1. REALNESS: How realistic and believable is this conversation? (1=obviously AI, 10=indistinguishable from human)
2. COHERENCE: How well does the conversation flow logically? (1=nonsensical, 10=perfect flow)
3. NATURALNESS: How natural do the speech patterns sound? (1=robotic, 10=completely natural)
4. OVERALL: Overall quality for training chatbot systems (1=unusable, 10=excellent training data)
5. HEALTHCARE_VALID: Is this actually a healthcare appointment conversation? (true/false)

Original prompt used:
{original_prompt[:500]}...

Generated conversation to grade:
{conversation[:2000]}..."""

def main():
    tester = PromptTester()
    tester.run_tests()

if __name__ == "__main__":
    main()