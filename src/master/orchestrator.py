#!/usr/bin/env python3
"""
Master Node Orchestrator - Main system coordinator
"""

import asyncio
import psycopg2
import json
import uuid
from datetime import datetime

class MasterOrchestrator:
    def __init__(self):
        self.db_config = {
            'host': 'EPM_DELL',
            'port': 5432,
            'database': 'calllab',
            'user': 'postgres',
            'password': 'pass'
        }
        self.running = False
        self.nodes = {}  # node_id -> last_seen
        
    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    async def start(self):
        """Start the master orchestrator"""
        print("🚀 Starting Master Orchestrator")
        
        # Verify database connection
        try:
            conn = self.get_db()
            conn.close()
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
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
            cur = conn.cursor()
            cur.execute(
                "SELECT id, hostname, status, last_seen FROM nodes WHERE node_type != 'master'"
            )
            nodes = cur.fetchall()
            cur.close()
            
            active_nodes = len([n for n in nodes if n[2] == 'online'])
            print(f"📡 Active nodes: {active_nodes}")
            
            conn.close()
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def job_scheduler_loop(self):
        """Schedule jobs to available nodes"""
        while self.running:
            conn = self.get_db()
            
            cur = conn.cursor()
            
            # Get pending jobs
            cur.execute(
                "SELECT id, scenario_id FROM jobs WHERE status = 'pending' ORDER BY created_at ASC"
            )
            pending_jobs = cur.fetchall()
            
            # Get available nodes
            cur.execute(
                "SELECT id, node_type FROM nodes WHERE status = 'online' AND node_type != 'master'"
            )
            available_nodes = cur.fetchall()
            
            # Assign jobs to nodes
            for job_id, scenario_id in pending_jobs[:len(available_nodes)]:
                # Simple assignment - first available node
                if available_nodes:
                    node_id, node_type = available_nodes.pop(0)
                    
                    # Update job status
                    cur.execute(
                        "UPDATE jobs SET status = 'running', assigned_node_id = %s, started_at = %s WHERE id = %s",
                        (node_id, datetime.now(), job_id)
                    )
                    
                    print(f"📋 Assigned job {job_id[:8]} to node {node_id[:8]}")
            
            conn.commit()
            cur.close()
            conn.close()
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def health_monitor_loop(self):
        """Monitor system health"""
        while self.running:
            conn = self.get_db()
            
            cur = conn.cursor()
            
            # Get system stats
            cur.execute("SELECT COUNT(*) FROM nodes WHERE status = 'online'")
            nodes_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM jobs WHERE status = 'pending'")
            pending_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM jobs WHERE status = 'running'")
            running_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM jobs WHERE status = 'completed'")
            completed_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM conversations")
            conv_count = cur.fetchone()[0]
            
            stats = {
                'nodes': nodes_count,
                'pending_jobs': pending_count,
                'running_jobs': running_count,
                'completed_jobs': completed_count,
                'conversations': conv_count
            }
            
            cur.close()
            
            print(f"💊 Health: {stats['nodes']} nodes, {stats['pending_jobs']} pending, {stats['running_jobs']} running, {stats['conversations']} conversations")
            
            conn.close()
            await asyncio.sleep(60)  # Check every minute
    
    def create_job(self, job_type, scenario_name, parameters=None):
        """Create a new job"""
        conn = self.get_db()
        
        cur = conn.cursor()
        
        # Get scenario ID
        cur.execute(
            "SELECT id FROM scenarios WHERE name = %s", (scenario_name,)
        )
        scenario = cur.fetchone()
        
        if not scenario:
            print(f"❌ Scenario not found: {scenario_name}")
            return None
        
        job_id = str(uuid.uuid4())
        
        cur.execute(
            "INSERT INTO jobs (id, scenario_id, parameters) VALUES (%s, %s, %s)",
            (job_id, scenario[0], json.dumps(parameters or {}))
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"Created job: {job_id}")
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