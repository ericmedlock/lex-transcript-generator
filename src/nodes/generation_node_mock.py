#!/usr/bin/env python3
"""
Mock Generation Node - For testing without LLM
"""

import asyncio
import sqlite3
import json
import uuid
import socket
import random
from datetime import datetime
from pathlib import Path

class MockGenerationNode:
    def __init__(self, db_path="data/transcript_platform.db"):
        self.db_path = db_path
        self.node_id = str(uuid.uuid4())
        self.hostname = socket.gethostname()
        self.running = False
        
    def get_db(self):
        return sqlite3.connect(self.db_path)
    
    async def register_node(self):
        conn = self.get_db()
        conn.execute(
            "INSERT OR REPLACE INTO nodes (id, hostname, node_type, status, capabilities) VALUES (?, ?, ?, ?, ?)",
            (self.node_id, self.hostname, "generation", "online", json.dumps(["mock_generation"]))
        )
        conn.commit()
        conn.close()
        print(f"📝 Registered MOCK generation node: {self.node_id[:8]} ({self.hostname})")
    
    async def start(self):
        print("🤖 Starting MOCK Generation Node")
        await self.register_node()
        self.running = True
        
        tasks = [
            asyncio.create_task(self.job_processor_loop()),
            asyncio.create_task(self.heartbeat_loop())
        ]
        
        print("✅ Mock generation node online")
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            await self.shutdown()
    
    async def job_processor_loop(self):
        while self.running:
            conn = self.get_db()
            
            job = conn.execute(
                "SELECT id, scenario_id, parameters FROM jobs WHERE assigned_node_id = ? AND status = 'running' LIMIT 1",
                (self.node_id,)
            ).fetchone()
            
            if job:
                job_id, scenario_id, parameters = job
                print(f"🔄 Processing MOCK job: {job_id[:8]}")
                
                # Simulate processing time
                await asyncio.sleep(2)
                
                # Generate mock conversation
                conversation = self.generate_mock_conversation(scenario_id)
                
                # Save conversation
                conv_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO conversations (id, job_id, scenario_id, content, quality_score) VALUES (?, ?, ?, ?, ?)",
                    (conv_id, job_id, scenario_id, json.dumps(conversation), random.uniform(0.7, 0.95))
                )
                
                # Mark job complete
                conn.execute(
                    "UPDATE jobs SET status = 'completed', completed_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), job_id)
                )
                
                print(f"✅ Completed MOCK job: {job_id[:8]} -> conversation: {conv_id[:8]}")
                conn.commit()
            
            conn.close()
            await asyncio.sleep(3)
    
    def generate_mock_conversation(self, scenario_id):
        """Generate a mock conversation"""
        mock_conversations = {
            "healthcare": [
                ("CUSTOMER", "Hi, I'd like to schedule an appointment with Dr. Smith."),
                ("AGENT", "Of course! I can help you with that. What type of appointment do you need?"),
                ("CUSTOMER", "It's for a routine check-up."),
                ("AGENT", "Perfect. I have availability next Tuesday at 2 PM or Thursday at 10 AM. Which works better?"),
                ("CUSTOMER", "Tuesday at 2 PM would be great."),
                ("AGENT", "Excellent! I've scheduled you for Tuesday, March 15th at 2 PM with Dr. Smith. Please arrive 15 minutes early.")
            ],
            "retail": [
                ("CUSTOMER", "Hi, I'd like to order a large pizza for delivery."),
                ("AGENT", "Great! What toppings would you like on your large pizza?"),
                ("CUSTOMER", "Pepperoni and mushrooms, please."),
                ("AGENT", "Perfect! One large pepperoni and mushroom pizza. What's your delivery address?"),
                ("CUSTOMER", "123 Main Street, apartment 4B."),
                ("AGENT", "Got it! Your total is $18.99 and delivery will be 25-30 minutes.")
            ]
        }
        
        # Get scenario domain
        conn = self.get_db()
        scenario = conn.execute("SELECT domain FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
        conn.close()
        
        domain = scenario[0] if scenario else "healthcare"
        turns = mock_conversations.get(domain, mock_conversations["healthcare"])
        
        return {
            "Participants": [
                {"ParticipantId": "A1", "ParticipantRole": "AGENT"},
                {"ParticipantId": "C1", "ParticipantRole": "CUSTOMER"}
            ],
            "Version": "1.1.0",
            "ContentMetadata": {"RedactionTypes": ["PII"], "Output": "Raw"},
            "CustomerMetadata": {"ContactId": str(uuid.uuid4())},
            "Transcript": [
                {
                    "ParticipantId": "C1" if role == "CUSTOMER" else "A1",
                    "Id": f"T{i:06d}",
                    "Content": content
                }
                for i, (role, content) in enumerate(turns, 1)
            ]
        }
    
    async def heartbeat_loop(self):
        while self.running:
            conn = self.get_db()
            conn.execute(
                "UPDATE nodes SET last_seen = ? WHERE id = ?",
                (datetime.now().isoformat(), self.node_id)
            )
            conn.commit()
            conn.close()
            await asyncio.sleep(30)
    
    async def shutdown(self):
        self.running = False
        conn = self.get_db()
        conn.execute("UPDATE nodes SET status = 'offline' WHERE id = ?", (self.node_id,))
        conn.commit()
        conn.close()
        print("👋 Mock generation node offline")

if __name__ == "__main__":
    asyncio.run(MockGenerationNode().start())