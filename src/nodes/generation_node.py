#!/usr/bin/env python3
"""
Generation Node - Handles LLM conversation generation
"""

import asyncio
import sqlite3
import json
import uuid
import socket
import aiohttp
from datetime import datetime
from pathlib import Path

class GenerationNode:
    def __init__(self, db_path="data/transcript_platform.db", llm_endpoint="http://127.0.0.1:1234/v1/chat/completions", max_jobs=None):
        self.db_path = db_path
        self.llm_endpoint = llm_endpoint
        self.node_id = str(uuid.uuid4())
        self.hostname = socket.gethostname()
        self.running = False
        self.max_jobs = max_jobs
        self.jobs_processed = 0
        
    def get_db(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    async def register_node(self):
        """Register this node with the master"""
        conn = self.get_db()
        
        # Check if node already exists
        existing = conn.execute(
            "SELECT id FROM nodes WHERE hostname = ? AND node_type = 'generation'", 
            (self.hostname,)
        ).fetchone()
        
        if existing:
            self.node_id = existing[0]
            # Update status
            conn.execute(
                "UPDATE nodes SET status = 'online', last_seen = ? WHERE id = ?",
                (datetime.now().isoformat(), self.node_id)
            )
        else:
            # Register new node
            conn.execute(
                "INSERT INTO nodes (id, hostname, node_type, status, capabilities) VALUES (?, ?, ?, ?, ?)",
                (self.node_id, self.hostname, "generation", "online", json.dumps(["llm_generation"]))
            )
        
        conn.commit()
        conn.close()
        
        print(f"📝 Registered generation node: {self.node_id[:8]} ({self.hostname})")
    
    async def start(self):
        """Start the generation node"""
        print("🤖 Starting Generation Node")
        
        if not Path(self.db_path).exists():
            print("❌ Database not found. Run: python scripts/db_setup.py init")
            return
        
        await self.register_node()
        self.running = True
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self.job_processor_loop()),
            asyncio.create_task(self.heartbeat_loop())
        ]
        
        print("✅ Generation node online")
        print(f"🔗 LLM endpoint: {self.llm_endpoint}")
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            await self.shutdown()
    
    async def job_processor_loop(self):
        """Process assigned generation jobs"""
        while self.running:
            conn = self.get_db()
            
            # Get jobs assigned to this node
            job = conn.execute(
                "SELECT id, scenario_id, parameters FROM jobs WHERE assigned_node_id = ? AND status = 'running' LIMIT 1",
                (self.node_id,)
            ).fetchone()
            
            if job:
                job_id, scenario_id, parameters = job
                params = json.loads(parameters or "{}")
                
                print(f"🔄 Processing job: {job_id[:8]}")
                
                try:
                    # Generate conversation
                    conversation = await self.generate_conversation(scenario_id, params)
                    
                    if conversation:
                        # Save conversation
                        conv_id = str(uuid.uuid4())
                        conn.execute(
                            "INSERT INTO conversations (id, job_id, scenario_id, content, quality_score) VALUES (?, ?, ?, ?, ?)",
                            (conv_id, job_id, scenario_id, json.dumps(conversation), 0.8)  # Default quality score
                        )
                        
                        # Mark job complete
                        conn.execute(
                            "UPDATE jobs SET status = 'completed', completed_at = ? WHERE id = ?",
                            (datetime.now().isoformat(), job_id)
                        )
                        
                        print(f"✅ Completed job: {job_id[:8]} -> conversation: {conv_id[:8]}")
                        
                        # Check if we've hit the job limit
                        self.jobs_processed += 1
                        if self.max_jobs and self.jobs_processed >= self.max_jobs:
                            print(f"🎯 Reached job limit ({self.max_jobs}), shutting down...")
                            self.running = False
                            return
                    else:
                        # Mark job failed
                        conn.execute(
                            "UPDATE jobs SET status = 'failed' WHERE id = ?", (job_id,)
                        )
                        print(f"❌ Failed job: {job_id[:8]}")
                
                except Exception as e:
                    print(f"❌ Error processing job {job_id[:8]}: {e}")
                    conn.execute(
                        "UPDATE jobs SET status = 'failed' WHERE id = ?", (job_id,)
                    )
                
                conn.commit()
            
            conn.close()
            await asyncio.sleep(5)  # Check every 5 seconds
    
    async def generate_conversation(self, scenario_id, parameters):
        """Generate a conversation using LLM"""
        conn = self.get_db()
        
        # Get scenario template
        scenario = conn.execute(
            "SELECT name, template FROM scenarios WHERE id = ?", (scenario_id,)
        ).fetchone()
        
        conn.close()
        
        if not scenario:
            return None
        
        scenario_name, template = scenario
        min_turns = parameters.get("min_turns", 20)
        max_turns = parameters.get("max_turns", 40)
        
        # Build prompt
        prompt = f"""Generate a realistic conversation for: {scenario_name}

{template}

Requirements:
- Length: {min_turns} to {max_turns} turns
- Format: alternating User: and Agent: lines
- Natural, realistic dialogue
- Include realistic hesitations and corrections

Generate ONLY the conversation, no commentary:"""
        
        try:
            # Call LLM
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "google/gemma-3-1b",  # LM Studio model
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.9,
                    "max_tokens": 2000
                }
                
                async with session.post(self.llm_endpoint, json=payload, timeout=60) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # Convert to Contact Lens format
                        return self.format_conversation(text, scenario_name)
                    else:
                        print(f"❌ LLM API error: {resp.status}")
                        return None
        
        except Exception as e:
            print(f"❌ LLM call failed: {e}")
            return None
    
    def format_conversation(self, text, scenario_name):
        """Convert raw text to Contact Lens format"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        turns = []
        
        for line in lines:
            if line.startswith("User:"):
                turns.append(("CUSTOMER", line[5:].strip()))
            elif line.startswith("Agent:"):
                turns.append(("AGENT", line[6:].strip()))
        
        # Build Contact Lens format
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
        """Send heartbeat to master"""
        while self.running:
            conn = self.get_db()
            conn.execute(
                "UPDATE nodes SET last_seen = ? WHERE id = ?",
                (datetime.now().isoformat(), self.node_id)
            )
            conn.commit()
            conn.close()
            
            await asyncio.sleep(30)  # Heartbeat every 30 seconds
    
    async def shutdown(self):
        """Shutdown node gracefully"""
        self.running = False
        
        conn = self.get_db()
        conn.execute(
            "UPDATE nodes SET status = 'offline' WHERE id = ?", (self.node_id,)
        )
        conn.commit()
        conn.close()
        
        print("👋 Generation node offline")

async def main():
    """Main entry point"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Generation Node")
    parser.add_argument("--endpoint", default="http://127.0.0.1:1234/v1/chat/completions", help="LLM endpoint URL")
    parser.add_argument("--max-jobs", type=int, help="Maximum jobs to process (debug mode)")
    
    args = parser.parse_args()
    
    node = GenerationNode(llm_endpoint=args.endpoint, max_jobs=args.max_jobs)
    await node.start()

if __name__ == "__main__":
    asyncio.run(main())