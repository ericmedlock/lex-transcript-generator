import csv
import os
from datetime import datetime
from typing import List, Dict

class CSVReporter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_report(self, test_results: List[Dict]) -> str:
        """Generate CSV report from test results"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prompt_test_results_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        fieldnames = [
            "model_id",
            "prompt_id", 
            "prompt_text",
            "generated_conversation",
            "grading_prompt",
            "tokens_per_second",
            "total_time",
            "total_tokens",
            "completion_tokens",
            "cpu_usage_avg",
            "cpu_usage_max", 
            "cpu_temp_avg",
            "cpu_temp_max",
            "gpu_usage_avg",
            "gpu_usage_max",
            "gpu_temp_avg", 
            "gpu_temp_max",
            "memory_usage_avg",
            "memory_usage_max",
            "realness_score",
            "coherence_score",
            "naturalness_score",
            "overall_score",
            "healthcare_valid",
            "brief_feedback",
            "grading_error",
            "execution_error",
            "timestamp"
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in test_results:
                # Flatten nested dictionaries
                row = {
                    "model_id": result.get("model_id", ""),
                    "prompt_id": result.get("prompt_id", ""),
                    "prompt_text": result.get("prompt_text", ""),
                    "generated_conversation": result.get("generated_conversation", ""),
                    "grading_prompt": result.get("grading_prompt", ""),
                    "tokens_per_second": result.get("performance_metrics", {}).get("tokens_per_second", 0),
                    "total_time": result.get("performance_metrics", {}).get("total_time", 0),
                    "total_tokens": result.get("performance_metrics", {}).get("total_tokens", 0),
                    "completion_tokens": result.get("performance_metrics", {}).get("completion_tokens", 0),
                    "cpu_usage_avg": result.get("resource_metrics", {}).get("cpu_usage_avg", 0),
                    "cpu_usage_max": result.get("resource_metrics", {}).get("cpu_usage_max", 0),
                    "cpu_temp_avg": result.get("resource_metrics", {}).get("cpu_temp_avg", 0),
                    "cpu_temp_max": result.get("resource_metrics", {}).get("cpu_temp_max", 0),
                    "gpu_usage_avg": result.get("resource_metrics", {}).get("gpu_usage_avg", 0),
                    "gpu_usage_max": result.get("resource_metrics", {}).get("gpu_usage_max", 0),
                    "gpu_temp_avg": result.get("resource_metrics", {}).get("gpu_temp_avg", 0),
                    "gpu_temp_max": result.get("resource_metrics", {}).get("gpu_temp_max", 0),
                    "memory_usage_avg": result.get("resource_metrics", {}).get("memory_usage_avg", 0),
                    "memory_usage_max": result.get("resource_metrics", {}).get("memory_usage_max", 0),
                    "realness_score": result.get("quality_scores", {}).get("realness_score", ""),
                    "coherence_score": result.get("quality_scores", {}).get("coherence_score", ""),
                    "naturalness_score": result.get("quality_scores", {}).get("naturalness_score", ""),
                    "overall_score": result.get("quality_scores", {}).get("overall_score", ""),
                    "healthcare_valid": result.get("quality_scores", {}).get("healthcare_valid", ""),
                    "brief_feedback": result.get("quality_scores", {}).get("brief_feedback", ""),
                    "grading_error": result.get("quality_scores", {}).get("grading_error", ""),
                    "execution_error": result.get("performance_metrics", {}).get("error", ""),
                    "timestamp": result.get("timestamp", "")
                }
                writer.writerow(row)
        
        print(f"Report generated: {filepath}")
        return filepath