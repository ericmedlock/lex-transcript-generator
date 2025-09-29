import os
import json
from openai import OpenAI
from typing import Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class QualityScorer:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    def score_conversation(self, conversation_text: str, prompt_used: str) -> Dict:
        """Score conversation quality using OpenAI with healthcare appointment focus"""
        
        grading_prompt = f"""Grade this AI-generated healthcare appointment conversation on a scale of 1-10 for each metric:

1. REALNESS: How realistic and believable is this conversation? (1=obviously AI, 10=indistinguishable from human)
2. COHERENCE: How well does the conversation flow logically? (1=nonsensical, 10=perfect flow)
3. NATURALNESS: How natural do the speech patterns sound? (1=robotic, 10=completely natural)
4. OVERALL: Overall quality for training chatbot systems (1=unusable, 10=excellent training data)
5. HEALTHCARE_VALID: Is this actually a healthcare appointment conversation? (true/false)

Original prompt used:
{prompt_used[:500]}...

Generated conversation to grade:
{conversation_text[:2000]}...

Respond ONLY with JSON format:
{{
  "realness_score": X,
  "coherence_score": X,
  "naturalness_score": X,
  "overall_score": X,
  "healthcare_valid": true/false,
  "brief_feedback": "one sentence explanation"
}}"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": grading_prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean JSON response
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            try:
                grades = json.loads(result_text)
                grades["grading_error"] = None
                return grades
            except json.JSONDecodeError:
                return {
                    "realness_score": None,
                    "coherence_score": None,
                    "naturalness_score": None,
                    "overall_score": None,
                    "healthcare_valid": None,
                    "brief_feedback": "",
                    "grading_error": f"Invalid JSON: {result_text[:100]}"
                }
                
        except Exception as e:
            return {
                "realness_score": None,
                "coherence_score": None,
                "naturalness_score": None,
                "overall_score": None,
                "healthcare_valid": None,
                "brief_feedback": "",
                "grading_error": str(e)
            }