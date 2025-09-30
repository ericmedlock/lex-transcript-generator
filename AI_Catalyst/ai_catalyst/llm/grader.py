#!/usr/bin/env python3
"""
Conversation Grader - AI_Catalyst component for grading conversations
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from .provider import LLMProvider

class ConversationGrader:
    """Grade conversations using three-tier LLM system"""
    
    def __init__(self, db_manager=None, config_manager=None):
        self.llm_provider = LLMProvider()
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.min_realness_score = 6
    
    def grade_conversation(self, conversation_text: str, conversation_id: Optional[str] = None, 
                          grader_type: str = "auto") -> Dict[str, Any]:
        """Grade a conversation using specified grader type"""
        
        grading_prompt = f"""Grade this AI-generated conversation on a scale of 1-10 for each metric:

1. REALNESS: How realistic and believable is this conversation? (1=obviously AI, 10=indistinguishable from human)
2. COHERENCE: How well does the conversation flow logically? (1=nonsensical, 10=perfect flow)
3. NATURALNESS: How natural do the speech patterns sound? (1=robotic, 10=completely natural)
4. OVERALL: Overall quality for training chatbot systems (1=unusable, 10=excellent training data)
5. HEALTHCARE_VALID: Is this actually a healthcare appointment conversation? (true/false)

Conversation to grade:
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
            response = self.llm_provider.generate_response(
                prompt=grading_prompt,
                provider_type=grader_type,
                temperature=0.1,
                max_tokens=200
            )
            
            # Clean JSON response
            result_text = response.strip()
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            grades = json.loads(result_text)
            grades["grading_error"] = None
            
            # Handle conversation deletion if needed
            should_delete = False
            if grades.get("healthcare_valid") == False and conversation_id:
                should_delete = True
                grades["delete_reason"] = "not_healthcare"
            elif grades.get("realness_score") and grades.get("realness_score") < self.min_realness_score and conversation_id:
                should_delete = True
                grades["delete_reason"] = f"low_realness_{grades.get('realness_score')}"
            
            if should_delete and self.db_manager:
                self._delete_invalid_conversation(conversation_id)
                grades["deleted"] = True
            
            return grades
            
        except json.JSONDecodeError as e:
            return {
                "realness_score": None,
                "coherence_score": None,
                "naturalness_score": None,
                "overall_score": None,
                "healthcare_valid": None,
                "grading_error": f"Invalid JSON: {str(e)[:100]}"
            }
        except Exception as e:
            return {
                "realness_score": None,
                "coherence_score": None,
                "naturalness_score": None,
                "overall_score": None,
                "healthcare_valid": None,
                "grading_error": str(e)
            }
    
    def _delete_invalid_conversation(self, conversation_id: str):
        """Delete conversation that failed validation"""
        if self.db_manager:
            try:
                self.db_manager.execute_query(
                    "DELETE FROM conversations WHERE id = %s",
                    (conversation_id,)
                )
            except Exception as e:
                print(f"Error deleting conversation {conversation_id[:8]}: {e}")
    
    def store_grades(self, conversation_id: str, grades: Dict[str, Any]) -> bool:
        """Store grades in database"""
        if not self.db_manager or grades.get("deleted"):
            return False
        
        try:
            grade_id = str(uuid.uuid4())
            self.db_manager.execute_query("""
                INSERT INTO conversation_grades 
                (id, conversation_id, realness_score, coherence_score, naturalness_score, 
                 overall_score, healthcare_valid, brief_feedback, grading_error, graded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                grade_id, conversation_id,
                grades.get("realness_score"),
                grades.get("coherence_score"), 
                grades.get("naturalness_score"),
                grades.get("overall_score"),
                grades.get("healthcare_valid"),
                grades.get("brief_feedback", ""),
                grades.get("grading_error", ""),
                datetime.now()
            ))
            return True
        except Exception as e:
            print(f"Error storing grades: {e}")
            return False