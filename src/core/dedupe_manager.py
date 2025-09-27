#!/usr/bin/env python3
"""
Deduplication Manager - Handles run-specific conversation deduplication
"""

import psycopg2
import json
import hashlib
import uuid
from datetime import datetime
import requests

class DedupeManager:
    def __init__(self):
        self.db_config = {
            'host': 'EPM_DELL',
            'port': 5432,
            'database': 'calllab',
            'user': 'postgres',
            'password': 'pass'
        }
        self.embedding_endpoint = "http://localhost:1234/v1"
        self.embedding_model = self.detect_embedding_model()
        
    def get_db(self):
        return psycopg2.connect(**self.db_config)
    
    def detect_embedding_model(self):
        """Detect available embedding model"""
        try:
            response = requests.get(f"{self.embedding_endpoint}/models", timeout=5)
            if response.status_code == 200:
                models = response.json().get("data", [])
                for model in models:
                    model_name = model["id"].lower()
                    if any(embed_type in model_name for embed_type in 
                           ['embedding', 'embed', 'nomic-embed', 'bge-', 'e5-']):
                        return model["id"]
        except Exception:
            pass
        return None
    
    def generate_embedding(self, text):
        """Generate embedding for text"""
        if not self.embedding_model:
            return None
        
        try:
            response = requests.post(
                f"{self.embedding_endpoint}/embeddings",
                json={"model": self.embedding_model, "input": text},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()["data"][0]["embedding"]
        except Exception:
            pass
        return None
    
    def get_or_create_run(self, target_conversations, similarity_threshold=0.85):
        """Get current active run or create new one"""
        conn = self.get_db()
        cur = conn.cursor()
        
        # Check for active run
        cur.execute("SELECT id, run_number FROM dedupe_runs WHERE status = 'active' ORDER BY created_at DESC LIMIT 1")
        active_run = cur.fetchone()
        
        if active_run:
            run_id, run_number = active_run
        else:
            # Create new run
            cur.execute("SELECT nextval('dedupe_run_counter')")
            run_number = cur.fetchone()[0]
            
            run_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO dedupe_runs (id, run_number, target_conversations, similarity_threshold) VALUES (%s, %s, %s, %s)",
                (run_id, run_number, target_conversations, similarity_threshold)
            )
            
            # Create run-specific table
            cur.execute("SELECT create_dedupe_table(%s)", (run_number,))
            
        conn.commit()
        cur.close()
        conn.close()
        
        return run_id, run_number
    
    def hash_conversation(self, conversation_content):
        """Generate hash for conversation content"""
        # Extract just the dialogue content for hashing
        if isinstance(conversation_content, dict):
            transcript = conversation_content.get("Transcript", [])
            content_text = " ".join([turn.get("Content", "") for turn in transcript])
        else:
            content_text = str(conversation_content)
        
        return hashlib.sha256(content_text.encode()).hexdigest()
    
    def is_duplicate(self, run_number, conversation_content, node_id, similarity_threshold=0.85):
        """Check if conversation is duplicate in current run"""
        conn = self.get_db()
        cur = conn.cursor()
        
        # Generate hash and embedding
        conv_hash = self.hash_conversation(conversation_content)
        
        # Check exact hash match first
        cur.execute(
            f"SELECT id FROM dedupe_conversations_run_{run_number} WHERE conversation_hash = %s",
            (conv_hash,)
        )
        if cur.fetchone():
            cur.close()
            conn.close()
            return True, "exact_hash"
        
        # Check semantic similarity
        if isinstance(conversation_content, dict):
            transcript = conversation_content.get("Transcript", [])
            content_text = " ".join([turn.get("Content", "") for turn in transcript])
        else:
            content_text = str(conversation_content)
        
        embedding = self.generate_embedding(content_text)
        if embedding:
            cur.execute(
                "SELECT * FROM check_similarity(%s, %s::vector, %s)",
                (run_number, embedding, similarity_threshold)
            )
            similar = cur.fetchone()
            if similar:
                cur.close()
                conn.close()
                return True, f"semantic_similarity_{similar[1]:.3f}"
        
        # Not duplicate - store it
        content_preview = content_text[:200] + "..." if len(content_text) > 200 else content_text
        metadata = {"node_id": node_id, "hash_method": "sha256"}
        
        cur.execute(
            f"""INSERT INTO dedupe_conversations_run_{run_number} 
               (conversation_hash, embedding, content_preview, node_id, metadata) 
               VALUES (%s, %s, %s, %s, %s)""",
            (conv_hash, embedding, content_preview, node_id, json.dumps(metadata))
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return False, "unique"
    
    def get_run_stats(self, run_number):
        """Get statistics for current run"""
        conn = self.get_db()
        cur = conn.cursor()
        
        cur.execute(f"SELECT COUNT(*) FROM dedupe_conversations_run_{run_number}")
        stored_count = cur.fetchone()[0]
        
        cur.execute("SELECT target_conversations FROM dedupe_runs WHERE run_number = %s", (run_number,))
        target = cur.fetchone()[0] if cur.fetchone() else 0
        
        cur.close()
        conn.close()
        
        return {"stored": stored_count, "target": target, "remaining": max(0, target - stored_count)}
    
    def close_run(self, run_number):
        """Mark run as completed"""
        conn = self.get_db()
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE dedupe_runs SET status = 'completed' WHERE run_number = %s",
            (run_number,)
        )
        
        conn.commit()
        cur.close()
        conn.close()