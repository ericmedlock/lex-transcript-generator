#!/usr/bin/env python3
"""
Master Node Orchestrator - Main system coordinator
"""

import asyncio
import psycopg2
import json
import uuid
import socket
import subprocess
import platform
from datetime import datetime, timedelta

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
        self.hostname = socket.gethostname()
        self.master_id = str(uuid.uuid4())
        self.heartbeat_interval = 10  # seconds
        self.failover_timeout = 60   # seconds
        self.network_check_timeout = 5  # seconds
        self.preferred_master = 'EPM_DELL'
        self.takeover_signal_sent = False
        
    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def check_existing_master(self):
        """Check if master is already running and decide whether to continue"""
        try:
            conn = self.get_db()
            cur = conn.cursor()
            
            # Check for existing masters with recent heartbeats
            cutoff_time = datetime.now() - timedelta(seconds=self.failover_timeout)
            cur.execute(
                "SELECT hostname, last_seen FROM nodes WHERE node_type = 'master' AND status = 'online' AND last_seen > %s ORDER BY last_seen DESC",
                (cutoff_time,)
            )
            active_masters = cur.fetchall()
            
            # Check stale masters
            cur.execute(
                "SELECT hostname, last_seen FROM nodes WHERE node_type = 'master' AND status = 'online' AND last_seen <= %s",
                (cutoff_time,)
            )
            stale_masters = cur.fetchall()
            
            # Clean up unreachable stale masters
            for hostname, last_seen in stale_masters:
                if not self.ping_host(hostname):
                    print(f"Removing unreachable stale master: {hostname}")
                    cur.execute(
                        "UPDATE nodes SET status = 'offline' WHERE hostname = %s AND node_type = 'master'",
                        (hostname,)
                    )
            
            conn.commit()
            
            # Re-check active masters after cleanup
            cur.execute(
                "SELECT hostname, last_seen FROM nodes WHERE node_type = 'master' AND status = 'online' AND last_seen > %s ORDER BY last_seen DESC",
                (cutoff_time,)
            )
            active_masters = cur.fetchall()
            
            cur.close()
            conn.close()
            
            if not active_masters:
                print(f"No active master found, starting on {self.hostname}")
                return True
        except Exception as e:
            print(f"Could not check for existing masters (DB unavailable): {e}")
            print(f"Starting master on {self.hostname} anyway")
            return True
        
        # Check if EPM_DELL is already running master
        epm_dell_running = any(master[0] == 'EPM_DELL' for master in existing_masters)
        
        if epm_dell_running and self.hostname != 'EPM_DELL':
            print(f"Master already running on EPM_DELL, shutting down {self.hostname}")
            return False
        
        if not epm_dell_running and self.hostname == 'EPM_DELL':
            print(f"EPM_DELL taking over master role from {existing_masters[0][0]}")
            # Signal other masters to shutdown gracefully
            conn = self.get_db()
            cur = conn.cursor()
            cur.execute(
                "UPDATE nodes SET status = 'shutdown_requested' WHERE node_type = 'master' AND hostname != %s",
                (self.hostname,)
            )
            conn.commit()
            cur.close()
            conn.close()
            return True
        
        if self.hostname in [master[0] for master in existing_masters]:
            print(f"Master already running on {self.hostname}, continuing")
            return True
        
        print(f"Master already running on {existing_masters[0][0]}, shutting down {self.hostname}")
        return False
    
    def register_master(self):
        """Register this instance as master node"""
        conn = self.get_db()
        cur = conn.cursor()
        
        # Check if master node already exists for this hostname
        cur.execute(
            "SELECT id FROM nodes WHERE hostname = %s AND node_type = 'master'",
            (self.hostname,)
        )
        existing = cur.fetchone()
        
        if existing:
            self.master_id = existing[0]
            # Update status
            cur.execute(
                "UPDATE nodes SET status = 'online', last_seen = %s WHERE id = %s",
                (datetime.now(), self.master_id)
            )
        else:
            # Register new master node
            cur.execute(
                "INSERT INTO nodes (id, hostname, node_type, status, capabilities) VALUES (%s, %s, %s, %s, %s)",
                (self.master_id, self.hostname, "master", "online", json.dumps(["orchestration", "job_scheduling"]))
            )
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"Registered master node: {self.master_id[:8]} ({self.hostname})")
    
    async def start(self):
        """Start the master orchestrator"""
        print(f"Starting Master Orchestrator on {self.hostname}")
        
        # Verify database connection
        try:
            conn = self.get_db()
            conn.close()
        except Exception as e:
            print(f"Database connection failed: {e}")
            return
        
        # Check if we should run based on existing masters
        if not self.check_existing_master():
            print("Exiting due to existing master")
            return
        
        # Register as master
        self.register_master()
        
        self.running = True
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self.heartbeat_loop()),
            asyncio.create_task(self.master_failover_monitor()),
            asyncio.create_task(self.node_discovery_loop()),
            asyncio.create_task(self.job_scheduler_loop()),
            asyncio.create_task(self.health_monitor_loop())
        ]
        
        print("Master node online")
        print("Monitoring nodes and jobs...")
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\nShutting down...")
            # Mark master as offline
            conn = self.get_db()
            cur = conn.cursor()
            cur.execute(
                "UPDATE nodes SET status = 'offline' WHERE id = %s",
                (self.master_id,)
            )
            conn.commit()
            cur.close()
            conn.close()
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
            print(f"Active nodes: {active_nodes}")
            
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
                    
                    print(f"Assigned job {job_id[:8]} to node {node_id[:8]}")
            
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
            
            print(f"Health: {stats['nodes']} nodes, {stats['pending_jobs']} pending, {stats['running_jobs']} running, {stats['conversations']} conversations")
            
            conn.close()
            await asyncio.sleep(60)  # Check every minute
    
    def ping_host(self, hostname):
        """Fast network connectivity check using ping"""
        try:
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", "2000", hostname]
            else:
                cmd = ["ping", "-c", "1", "-W", "2", hostname]
            
            result = subprocess.run(cmd, capture_output=True, timeout=self.network_check_timeout)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def heartbeat_loop(self):
        """Send regular heartbeats and check for shutdown signals"""
        while self.running:
            try:
                conn = self.get_db()
                cur = conn.cursor()
                
                # Update heartbeat
                cur.execute(
                    "UPDATE nodes SET last_seen = %s WHERE id = %s",
                    (datetime.now(), self.master_id)
                )
                
                # Check if we've been asked to shutdown (preferred node takeover)
                cur.execute(
                    "SELECT status FROM nodes WHERE id = %s",
                    (self.master_id,)
                )
                status = cur.fetchone()
                
                if status and status[0] == 'shutdown_requested':
                    print(f"Shutdown requested by preferred master, gracefully exiting...")
                    cur.execute(
                        "UPDATE nodes SET status = 'offline' WHERE id = %s",
                        (self.master_id,)
                    )
                    conn.commit()
                    cur.close()
                    conn.close()
                    self.running = False
                    return
                
                conn.commit()
                cur.close()
                conn.close()
            except Exception as e:
                print(f"Heartbeat failed: {e}")
            
            await asyncio.sleep(self.heartbeat_interval)
    
    async def master_failover_monitor(self):
        """Monitor for failed masters and preferred node takeover"""
        while self.running:
            try:
                conn = self.get_db()
                cur = conn.cursor()
                
                # Check for failed masters
                cutoff_time = datetime.now() - timedelta(seconds=self.failover_timeout)
                cur.execute(
                    "SELECT hostname, last_seen FROM nodes WHERE node_type = 'master' AND status = 'online' AND hostname != %s AND last_seen <= %s",
                    (self.hostname, cutoff_time)
                )
                failed_masters = cur.fetchall()
                
                for hostname, last_seen in failed_masters:
                    if not self.ping_host(hostname):
                        print(f"Taking over from failed master: {hostname}")
                        cur.execute(
                            "UPDATE nodes SET status = 'offline' WHERE hostname = %s AND node_type = 'master'",
                            (hostname,)
                        )
                
                # Preferred node takeover logic
                if self.hostname == self.preferred_master and not self.takeover_signal_sent:
                    cur.execute(
                        "SELECT hostname FROM nodes WHERE node_type = 'master' AND status = 'online' AND hostname != %s",
                        (self.hostname,)
                    )
                    other_masters = cur.fetchall()
                    
                    if other_masters:
                        print(f"Preferred master {self.hostname} requesting takeover from {[m[0] for m in other_masters]}")
                        cur.execute(
                            "UPDATE nodes SET status = 'shutdown_requested' WHERE node_type = 'master' AND hostname != %s",
                            (self.hostname,)
                        )
                        self.takeover_signal_sent = True
                
                conn.commit()
                cur.close()
                conn.close()
            except Exception as e:
                print(f"Failover monitor error: {e}")
            
            await asyncio.sleep(20)
    
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
            print(f"Scenario not found: {scenario_name}")
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
    
    # Create some sample jobs for testing (only if DB is available)
    try:
        orchestrator.create_job("generate", "Healthcare Appointment Scheduling", {"min_turns": 20, "max_turns": 40})
        orchestrator.create_job("generate", "Pizza Order Placement", {"min_turns": 15, "max_turns": 30})
    except Exception as e:
        print(f"Could not create sample jobs: {e}")
    
    await orchestrator.start()

if __name__ == "__main__":
    asyncio.run(main())