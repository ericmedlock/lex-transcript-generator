#!/usr/bin/env python3
"""Multi-threaded conversation grader with CPU/GPU throttling"""

import psycopg2
import json
import uuid
import threading
import time
import queue
import psutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import GPUtil
except ImportError:
    GPUtil = None

class ThrottledGrader:
    def __init__(self, max_workers=5, cpu_limit=80, gpu_limit=85):
        self.max_workers = max_workers
        self.cpu_limit = cpu_limit
        self.gpu_limit = gpu_limit
        self.db_config = {
            'host': 'EPM_DELL',
            'port': 5432,
            'database': 'calllab',
            'user': 'postgres',
            'password': 'pass'
        }
        self.graded_count = 0
        self.total_count = 0
        self.lock = threading.Lock()
        
    def get_system_load(self):
        """Get current CPU and GPU usage"""
        cpu_usage = psutil.cpu_percent(interval=0.1)
        gpu_usage = 0
        
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_usage = max(gpu.load * 100 for gpu in gpus)
            except:
                pass
                
        return cpu_usage, gpu_usage
    
    def should_throttle(self):
        """Check if we should throttle based on system load"""
        cpu_usage, gpu_usage = self.get_system_load()
        return cpu_usage > self.cpu_limit or gpu_usage > self.gpu_limit
    
    def grade_conversation_local(self, conversation_text):
        """Simple local grading"""
        lines = conversation_text.strip().split('\n')
        word_count = len(conversation_text.split())
        
        if word_count > 100 and len(lines) > 10:
            realness_score = 8
        elif word_count > 50 and len(lines) > 5:
            realness_score = 7
        else:
            realness_score = 6
        
        healthcare_keywords = ['appointment', 'doctor', 'checkup', 'medical', 'health', 'patient', 'clinic', 'schedule']
        healthcare_valid = any(keyword in conversation_text.lower() for keyword in healthcare_keywords)
        
        coherence_score = 8 if len(lines) > 8 else 7
        naturalness_score = 8 if '?' in conversation_text and word_count > 80 else 7
        overall_score = round((realness_score + coherence_score + naturalness_score) / 3)
        
        return {
            "realness_score": realness_score,
            "coherence_score": coherence_score,
            "naturalness_score": naturalness_score,
            "overall_score": overall_score,
            "healthcare_valid": healthcare_valid,
            "brief_feedback": f"Threaded grading: {word_count} words, {len(lines)} turns",
            "grading_error": None
        }
    
    def grade_single_conversation(self, conv_data):
        """Grade a single conversation with throttling"""
        conv_id, content = conv_data
        
        # Throttle if system is under heavy load
        while self.should_throttle():
            time.sleep(2)
        
        try:
            # Parse conversation content
            content_data = json.loads(content) if isinstance(content, str) else content
            
            conversation_text = ""
            if "Transcript" in content_data:
                for turn in content_data["Transcript"]:
                    conversation_text += f"{turn.get('Content', '')}\n"
            else:
                conversation_text = str(content_data)
            
            if not conversation_text.strip():
                return None
            
            # Grade conversation
            grades = self.grade_conversation_local(conversation_text)
            
            # Store in database
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            grade_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO conversation_grades 
                (id, conversation_id, realness_score, coherence_score, naturalness_score, 
                 overall_score, healthcare_valid, brief_feedback, grading_error, graded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                grade_id, conv_id,
                grades["realness_score"],
                grades["coherence_score"], 
                grades["naturalness_score"],
                grades["overall_score"],
                grades["healthcare_valid"],
                grades["brief_feedback"],
                grades["grading_error"],
                datetime.now()
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            with self.lock:
                self.graded_count += 1
                if self.graded_count % 10 == 0:
                    print(f"  Graded {self.graded_count}/{self.total_count} conversations")
            
            return grades
            
        except Exception as e:
            print(f"  Error grading {conv_id[:8]}: {e}")
            return None
    
    def get_ungraded_conversations(self, limit=50):
        """Get batch of ungraded conversations"""
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT c.id, c.content
            FROM conversations c
            WHERE NOT EXISTS (SELECT 1 FROM conversation_grades WHERE conversation_id = c.id)
            ORDER BY c.created_at DESC
            LIMIT %s
        """, (limit,))
        
        conversations = cur.fetchall()
        cur.close()
        conn.close()
        
        return conversations
    
    def grade_batch_threaded(self, limit=None):
        """Grade conversations using multiple threads with throttling"""
        print(f"Starting threaded grading with {self.max_workers} workers...")
        
        total_graded = 0
        
        while True:
            # Get batch of conversations
            conversations = self.get_ungraded_conversations(50)
            if not conversations:
                break
                
            self.total_count = len(conversations)
            self.graded_count = 0
            
            print(f"Grading batch of {len(conversations)} conversations...")
            
            # Process batch with thread pool
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_conv = {
                    executor.submit(self.grade_single_conversation, conv): conv 
                    for conv in conversations
                }
                
                # Process completed tasks
                for future in as_completed(future_to_conv):
                    result = future.result()
                    if result:
                        total_graded += 1
            
            print(f"Completed batch. Total graded: {total_graded}")
            
            # Break if we have a limit and reached it
            if limit and total_graded >= limit:
                break
        
        print(f"Threaded grading complete: {total_graded} conversations graded")
        return total_graded

def grade_database_conversations_threaded(limit=None, max_workers=5):
    """Main function for threaded grading"""
    grader = ThrottledGrader(max_workers=max_workers)
    return grader.grade_batch_threaded(limit=limit)

if __name__ == "__main__":
    grade_database_conversations_threaded()