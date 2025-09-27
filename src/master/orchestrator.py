#!/usr/bin/env python3
"""
Master Node Orchestrator - Main system coordinator
"""

import asyncio
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

class MasterOrchestrator:
    def __init__(self, db_path="data/transcript_platform.db"):
        self.db_path = db_path
        self.running = False
        self.nodes = {}  # node_id -> last_seen
        
    def get_db(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    async def start(self):
        """Start the master orchestrator"""
        print("🚀 Starting Master Orchestrator")
        
        # Verify database exists
        if not Path(self.db_path).exists():
            print("❌ Database not found. Run: python scripts/db_setup.py init")
            return
        
        self.running = True
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self.node_discovery_loop()),
            asyncio.create_task(self.job_scheduler_loop()),
            asyncio.create_task(self.health_monitor_loop())
        ]
        
        print("✅ Master node online")
        print("📊 Monitoring nodes and jobs...")
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self.running = False
    
    async def node_discovery_loop(self):
        """Discover and track worker nodes"""
        while self.running:
            # TODO: Implement actual node discovery (network scan, heartbeats)
            # For now, just check database
            
            conn = self.get_db()
            nodes = conn.execute(
                "SELECT id, hostname, status, last_seen FROM nodes WHERE node_type != 'master'"
            ).fetchall()
            
            active_nodes = len([n for n in nodes if n[2] == 'online'])
            print(f"📡 Active nodes: {active_nodes}")
            
            conn.close()
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def job_scheduler_loop(self):
        """Schedule jobs to available nodes"""
        while self.running:
            conn = self.get_db()
            
            # Get pending jobs
            pending_jobs = conn.execute(
                "SELECT id, job_type, priority FROM jobs WHERE status = 'pending' ORDER BY priority DESC, created_at ASC"
            ).fetchall()
            
            # Get available nodes
            available_nodes = conn.execute(
                "SELECT id, node_type FROM nodes WHERE status = 'online' AND node_type != 'master'"
            ).fetchall()
            
            # Assign jobs to nodes
            for job_id, job_type, priority in pending_jobs[:len(available_nodes)]:
                # Simple assignment - first available node
                if available_nodes:
                    node_id, node_type = available_nodes.pop(0)
                    
                    # Update job status
                    conn.execute(
                        "UPDATE jobs SET status = 'running', assigned_node_id = ?, started_at = ? WHERE id = ?",
                        (node_id, datetime.now().isoformat(), job_id)
                    )
                    
                    print(f"📋 Assigned job {job_id[:8]} to node {node_id[:8]}")
            
            conn.commit()
            conn.close()
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def health_monitor_loop(self):
        """Monitor system health"""
        while self.running:
            conn = self.get_db()
            
            # Get system stats
            stats = {
                'nodes': conn.execute("SELECT COUNT(*) FROM nodes WHERE status = 'online'").fetchone()[0],
                'pending_jobs': conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'pending'").fetchone()[0],
                'running_jobs': conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'running'").fetchone()[0],
                'completed_jobs': conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'completed'").fetchone()[0],
                'conversations': conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            }
            
            print(f"💊 Health: {stats['nodes']} nodes, {stats['pending_jobs']} pending, {stats['running_jobs']} running, {stats['conversations']} conversations")
            
            conn.close()
            await asyncio.sleep(60)  # Check every minute
    
    def create_job(self, job_type, scenario_name, parameters=None):
        """Create a new job"""
        conn = self.get_db()
        
        # Get scenario ID
        scenario = conn.execute(
            "SELECT id FROM scenarios WHERE name = ?", (scenario_name,)
        ).fetchone()
        
        if not scenario:
            print(f"❌ Scenario not found: {scenario_name}")
            return None
        
        job_id = str(uuid.uuid4())
        
        conn.execute(
            "INSERT INTO jobs (id, job_type, scenario_id, parameters) VALUES (?, ?, ?, ?)",
            (job_id, job_type, scenario[0], json.dumps(parameters or {}))
        )
        
        conn.commit()
        conn.close()
        
        print(f"✅ Created job: {job_id}")
        return job_id

async def main():
    """Main entry point"""
    orchestrator = MasterOrchestrator()
    
    # Create some sample jobs for testing
    orchestrator.create_job("generate", "Healthcare Appointment Scheduling", {"min_turns": 20, "max_turns": 40})
    orchestrator.create_job("generate", "Pizza Order Placement", {"min_turns": 15, "max_turns": 30})
    
    await orchestrator.start()

if __name__ == "__main__":
    asyncio.run(main())