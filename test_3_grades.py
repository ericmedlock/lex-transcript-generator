#!/usr/bin/env python3
"""Test grading on just 3 conversations"""

from src.core.conversation_grader import ConversationGrader

grader = ConversationGrader()
graded_count = grader.grade_database_conversations(limit=3, grader_type="local")
print(f"Graded {graded_count} conversations")