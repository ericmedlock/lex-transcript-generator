#!/usr/bin/env python3
"""
Generation Node - Handles LLM conversation generation
"""

import asyncio
import psycopg2
import json
import uuid
import socket
import aiohttp
import sys
import os
from datetime import datetime
from pathlib import Path

class GenerationNode:
    def __init__(self, llm_endpoint="http://127.0.0.1:1234/v1/chat/completions", max_jobs=None):
        self.db_config = {
            'host': 'EPM_DELL',
            'port': 5432,
            'database': 'calllab',
            'user': 'postgres',
            'password': 'pass'
        }
        self.llm_endpoint = llm_endpoint
        self.node_id = str(uuid.uuid4())
        self.hostname = socket.gethostname()
        self.running = False
        self.max_jobs = max_jobs
        self.jobs_processed = 0
        self.rag_preprocessor = self.init_rag()
        
    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def init_rag(self):
        """Initialize RAG preprocessor"""
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data'))
            from rag_preprocessor import RAGPreprocessor
            return RAGPreprocessor()
        except Exception as e:
            print(f"Warning: RAG not available: {e}")
            return None
    
    def rag_search(self, query, limit=3):
        """Search for similar conversations using RAG"""
        if not self.rag_preprocessor:
            return ""
        
        try:
            results = self.rag_preprocessor.search_similar(query, limit)
            if not results:
                return ""
            
            examples = []
            for i, result in enumerate(results, 1):
                # Truncate to first 300 characters
                content = result['content'][:300]
                if len(result['content']) > 300:
                    content += "..."
                examples.append(f"Example {i}:\n{content}\n")
            
            return "\n".join(examples)
        except Exception as e:
            print(f"RAG search error: {e}")
            return ""
    
    async def register_node(self):
        """Register this node with the master"""
        conn = self.get_db()
        
        cur = conn.cursor()
        
        # Check if node already exists
        cur.execute(
            "SELECT id FROM nodes WHERE hostname = %s AND node_type = 'generation'", 
            (self.hostname,)
        )
        existing = cur.fetchone()
        
        if existing:
            self.node_id = existing[0]
            # Update status
            cur.execute(
                "UPDATE nodes SET status = 'online', last_seen = %s WHERE id = %s",
                (datetime.now(), self.node_id)
            )
        else:
            # Register new node
            cur.execute(
                "INSERT INTO nodes (id, hostname, node_type, status, capabilities) VALUES (%s, %s, %s, %s, %s)",
                (self.node_id, self.hostname, "generation", "online", json.dumps(["llm_generation"]))
            )
        
        cur.close()
        
        conn.commit()
        conn.close()
        
        print(f"Registered generation node: {self.node_id[:8]} ({self.hostname})")
    
    async def start(self):
        """Start the generation node"""
        print("Starting Generation Node")
        
        try:
            conn = self.get_db()
            conn.close()
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return
        
        await self.register_node()
        self.running = True
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self.job_processor_loop()),
            asyncio.create_task(self.heartbeat_loop())
        ]
        
        print("Generation node online")
        print(f"LLM endpoint: {self.llm_endpoint}")
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\nShutting down...")
            await self.shutdown()
    
    async def job_processor_loop(self):
        """Process assigned generation jobs"""
        while self.running:
            conn = self.get_db()
            cur = conn.cursor()
            
            # Get jobs assigned to this node
            cur.execute(
                "SELECT id, scenario_id, parameters FROM jobs WHERE assigned_node_id = %s AND status = 'running' LIMIT 1",
                (self.node_id,)
            )
            job = cur.fetchone()
            
            if job:
                job_id, scenario_id, parameters = job
                params = parameters if isinstance(parameters, dict) else json.loads(parameters or "{}")
                
                print(f"Processing job: {job_id[:8]}")
                
                try:
                    # Generate conversation
                    conversation = await self.generate_conversation(scenario_id, params)
                    
                    if conversation:
                        # Extract metadata
                        metadata = conversation.pop("_metadata", {})
                        
                        # Save conversation
                        conv_id = str(uuid.uuid4())
                        cur.execute(
                            """INSERT INTO conversations 
                               (id, job_id, scenario_id, content, quality_score, model_name, 
                                generation_start_time, generation_end_time, generation_duration_ms, evaluation_metrics) 
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (conv_id, job_id, scenario_id, json.dumps(conversation), 0.8,
                             metadata.get("model_name"), metadata.get("start_time"), 
                             metadata.get("end_time"), metadata.get("duration_ms"), 
                             json.dumps({"realness_score": None, "speed_score": None, "gan_score": None}))
                        )
                        
                        # Mark job complete
                        cur.execute(
                            "UPDATE jobs SET status = 'completed', completed_at = %s WHERE id = %s",
                            (datetime.now(), job_id)
                        )
                        
                        print(f"Completed job: {job_id[:8]} -> conversation: {conv_id[:8]}")
                        
                        # Check if we've hit the job limit (only count successful jobs)
                        self.jobs_processed += 1
                        if self.max_jobs and self.jobs_processed >= self.max_jobs:
                            print(f"Reached job limit ({self.max_jobs}), shutting down...")
                            self.running = False
                            return
                    else:
                        # Mark job failed (don't increment counter)
                        cur.execute(
                            "UPDATE jobs SET status = 'failed' WHERE id = %s", (job_id,)
                        )
                        print(f"Failed job: {job_id[:8]} - not counting toward limit")
                
                except Exception as e:
                    print(f"Error processing job {job_id[:8]}: {e}")
                    cur.execute(
                        "UPDATE jobs SET status = 'failed' WHERE id = %s", (job_id,)
                    )
                    print(f"Job failed due to exception - not counting toward limit")
                
                conn.commit()
            
            cur.close()
            conn.close()
            await asyncio.sleep(5)  # Check every 5 seconds
    
    async def get_available_model(self):
        """Get first available model from LM Studio using config"""
        try:
            # Get first available model from API
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.llm_endpoint.replace('/chat/completions', '/models')}", timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = data.get("data", [])
                        if models:
                            return models[0]["id"]
        except Exception as e:
            print(f"Could not get models, using default: {e}")
        
        return "microsoft/phi-4-mini-reasoning"  # Fallback
    
    async def generate_conversation(self, scenario_id, parameters):
        """Generate a conversation using LLM"""
        conn = self.get_db()
        cur = conn.cursor()
        
        # Get scenario template
        cur.execute(
            "SELECT name, template FROM scenarios WHERE id = %s", (scenario_id,)
        )
        scenario = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not scenario:
            return None
        
        scenario_name, template = scenario
        min_turns = parameters.get("min_turns", 20)
        max_turns = parameters.get("max_turns", 40)
        
        # Get available model
        model_name = await self.get_available_model()
        
        # Search for similar conversations
        rag_examples = self.rag_search(f"{scenario_name} {template}", limit=3)
        
        # Build enhanced prompt with examples
        if rag_examples:
            prompt = f"""Based on these real conversation examples:

{rag_examples}

Now generate a similar realistic conversation for: {scenario_name}

{template}

Requirements:
- Length: {min_turns} to {max_turns} turns
- Format: alternating User: and Agent: lines
- Natural, realistic dialogue like the examples above
- Include realistic hesitations and corrections

Generate ONLY the conversation, no commentary:"""
        else:
            # Fallback to original prompt if no RAG examples
            prompt = f"""Generate a realistic conversation for: {scenario_name}

{template}

Requirements:
- Length: {min_turns} to {max_turns} turns
- Format: alternating User: and Agent: lines
- Natural, realistic dialogue
- Include realistic hesitations and corrections

Generate ONLY the conversation, no commentary:"""
        
        start_time = datetime.now()
        
        try:
            # Call LLM
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.9,
                    "max_tokens": 2000
                }
                
                async with session.post(self.llm_endpoint, json=payload, timeout=60) as resp:
                    end_time = datetime.now()
                    duration_ms = int((end_time - start_time).total_seconds() * 1000)
                    
                    if resp.status == 200:
                        data = await resp.json()
                        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # Convert to Contact Lens format and add metadata
                        conversation = self.format_conversation(text, scenario_name)
                        conversation["_metadata"] = {
                            "model_name": model_name,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat(),
                            "duration_ms": duration_ms,
                            "rag_examples_used": bool(rag_examples)
                        }
                        
                        return conversation
                    else:
                        print(f"LLM API error: {resp.status}")
                        return None
        
        except Exception as e:
            print(f"LLM call failed: {e}")
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
            cur = conn.cursor()
            cur.execute(
                "UPDATE nodes SET last_seen = %s WHERE id = %s",
                (datetime.now(), self.node_id)
            )
            conn.commit()
            cur.close()
            conn.close()
            
            await asyncio.sleep(30)  # Heartbeat every 30 seconds
    
    async def shutdown(self):
        """Shutdown the node"""
        self.running = False

if __name__ == "__main__":
    import sys
    max_jobs = int(sys.argv[1]) if len(sys.argv) > 1 else None
    node = GenerationNode(max_jobs=max_jobs)
    asyncio.run(node.start())