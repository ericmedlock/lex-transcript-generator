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
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path

class ConfigManager:
    """Enhanced configuration management"""
    
    def __init__(self, config_path=None):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration with fallback hierarchy"""
        # Config file search order
        search_paths = []
        if self.config_path:
            search_paths.append(self.config_path)
        search_paths.extend([
            "orchestrator_config.json",
            "config/orchestrator_config.json"
        ])
        
        for path in search_paths:
            if Path(path).exists():
                try:
                    with open(path, 'r') as f:
                        config = json.load(f)
                    
                    # Validate critical settings
                    self.validate_config(config)
                    print(f"[CONFIG] Loaded from: {path}")
                    return config
                except Exception as e:
                    print(f"[CONFIG] Error loading {path}: {e}")
                    continue
        
        print("[CONFIG] No config file found, creating new config...")
        new_config = self.create_interactive_config()
        
        # Save to default location
        Path("config").mkdir(exist_ok=True)
        with open("config/orchestrator_config.json", 'w') as f:
            json.dump(new_config, f, indent=2)
        
        print("[CONFIG] Saved orchestrator config")
        return new_config
    
    def validate_config(self, config):
        """Validate configuration settings and connectivity"""
        # Validate database connection
        db_config = config.get("db_config", {})
        if db_config:
            try:
                import psycopg2
                conn = psycopg2.connect(**db_config)
                conn.close()
                print(f"[CONFIG] Database connection OK: {db_config.get('host')}:{db_config.get('port')}")
            except Exception as e:
                raise ValueError(f"Database connection failed: {e}")
        
        # Validate LLM endpoint if present
        llm_endpoint = config.get("llm_endpoint")
        if llm_endpoint:
            try:
                import requests
                models_url = llm_endpoint.replace('/chat/completions', '/models')
                resp = requests.get(models_url, timeout=5)
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    print(f"[CONFIG] LLM endpoint OK: {len(models)} models available")
                else:
                    print(f"[CONFIG] Warning: LLM endpoint returned {resp.status_code}")
            except Exception as e:
                print(f"[CONFIG] Warning: LLM endpoint check failed: {e}")
        
        # Validate job creation settings
        job_config = config.get("job_creation", {})
        total_conversations = job_config.get("total_conversations", 100)
        conversations_per_job = job_config.get("conversations_per_job", 10)
        
        if total_conversations <= 0 or conversations_per_job <= 0:
            raise ValueError("total_conversations and conversations_per_job must be positive")
        
        print(f"[CONFIG] Job config OK: {total_conversations} conversations, {conversations_per_job} per job")
    
    def get_default_config(self):
        """Default configuration"""
        return {
            "heartbeat_interval": 10,
            "failover_timeout": 60,
            "network_check_timeout": 5,
            "preferred_master": "EPM_DELL",
            "db_config": {
                "host": "EPM_DELL",
                "port": 5432,
                "database": "calllab",
                "user": "postgres",
                "password": "pass"
            },
            "job_creation": {
                "total_conversations": 1000,
                "conversations_per_job": 10,
                "pending_queue_size": 10,
                "check_interval": 30
            },
            "health_monitor": {
                "check_interval": 60,
                "node_timeout": 300
            }
        }
    
    def create_interactive_config(self):
        """Create orchestrator configuration interactively"""
        defaults = self.get_default_config()
        config = {}
        
        print(f"\nConfiguring orchestrator (master node)")
        print("Press Enter to accept defaults, or type new value:\n")
        
        # Basic settings
        config["heartbeat_interval"] = int(input(f"Heartbeat interval seconds [{defaults['heartbeat_interval']}]: ") or defaults["heartbeat_interval"])
        config["failover_timeout"] = int(input(f"Failover timeout seconds [{defaults['failover_timeout']}]: ") or defaults["failover_timeout"])
        config["preferred_master"] = input(f"Preferred master hostname [{defaults['preferred_master']}]: ") or defaults["preferred_master"]
        
        # Database config
        config["db_config"] = {}
        config["db_config"]["host"] = input(f"Database host [{defaults['db_config']['host']}]: ") or defaults["db_config"]["host"]
        config["db_config"]["port"] = int(input(f"Database port [{defaults['db_config']['port']}]: ") or defaults["db_config"]["port"])
        config["db_config"]["database"] = input(f"Database name [{defaults['db_config']['database']}]: ") or defaults["db_config"]["database"]
        config["db_config"]["user"] = input(f"Database user [{defaults['db_config']['user']}]: ") or defaults["db_config"]["user"]
        config["db_config"]["password"] = input(f"Database password [{defaults['db_config']['password']}]: ") or defaults["db_config"]["password"]
        
        # Job creation settings
        config["job_creation"] = {}
        config["job_creation"]["total_conversations"] = int(input(f"Total conversations to generate [{defaults['job_creation']['total_conversations']}]: ") or defaults["job_creation"]["total_conversations"])
        config["job_creation"]["conversations_per_job"] = int(input(f"Conversations per job [{defaults['job_creation']['conversations_per_job']}]: ") or defaults["job_creation"]["conversations_per_job"])
        config["job_creation"]["pending_queue_size"] = int(input(f"Pending job queue size [{defaults['job_creation']['pending_queue_size']}]: ") or defaults["job_creation"]["pending_queue_size"])
        
        # Health monitoring
        config["health_monitor"] = {}
        config["health_monitor"]["check_interval"] = int(input(f"Health check interval seconds [{defaults['health_monitor']['check_interval']}]: ") or defaults["health_monitor"]["check_interval"])
        config["health_monitor"]["node_timeout"] = int(input(f"Node timeout seconds [{defaults['health_monitor']['node_timeout']}]: ") or defaults["health_monitor"]["node_timeout"])
        
        # Set remaining defaults
        config["network_check_timeout"] = defaults["network_check_timeout"]
        config["job_creation"]["check_interval"] = defaults["job_creation"]["check_interval"]
        
        return config
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def setup_output_directory(self, job_type, job_id):
        """Create machine-specific output directory"""
        machine_name = self.config.get("machine_name", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output") / machine_name / f"{job_type}_{job_id}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def generate_filename(self, file_type, extension="csv"):
        """Generate machine-prefixed filename"""
        machine_name = self.config.get("machine_name", "unknown")
        return f"{machine_name}_{file_type}.{extension}"

class MasterOrchestrator:
    def __init__(self, config_path=None):
        self.config_manager = ConfigManager(config_path)
        self.db_config = self.config_manager.get("db_config", {
            'host': 'EPM_DELL',
            'port': 5432,
            'database': 'calllab',
            'user': 'postgres',
            'password': 'pass'
        })
        self.running = False
        self.nodes = {}  # node_id -> {last_seen, capabilities, performance}
        self.hostname = socket.gethostname()
        self.master_id = str(uuid.uuid4())
        self.heartbeat_interval = self.config_manager.get("heartbeat_interval", 10)
        self.failover_timeout = self.config_manager.get("failover_timeout", 60)
        self.network_check_timeout = self.config_manager.get("network_check_timeout", 5)
        self.preferred_master = self.config_manager.get("preferred_master", 'EPM_DELL')
        self.takeover_signal_sent = False
        self.current_run_id = None
        self.target_jobs = 0
        self.jobs_created = 0
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.running = False
        
    def get_db(self, retries=3):
        """Get database connection with retry logic"""
        for attempt in range(retries):
            try:
                return psycopg2.connect(**self.db_config)
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                print(f"Database connection failed (attempt {attempt + 1}/{retries}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
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
        epm_dell_running = any(master[0] == 'EPM_DELL' for master in active_masters)
        
        if epm_dell_running and self.hostname != 'EPM_DELL':
            print(f"Master already running on EPM_DELL, shutting down {self.hostname}")
            return False
        
        if not epm_dell_running and self.hostname == 'EPM_DELL' and active_masters:
            print(f"EPM_DELL taking over master role from {active_masters[0][0]}")
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
        
        if self.hostname in [master[0] for master in active_masters]:
            print(f"Master already running on {self.hostname}, continuing")
            return True
        
        if active_masters:
            print(f"Master already running on {active_masters[0][0]}, shutting down {self.hostname}")
            return False
        
        return True
    
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
        
        # Get next run ID
        try:
            cur.execute(
                "UPDATE run_counter SET current_run = current_run + 1 RETURNING current_run"
            )
            result = cur.fetchone()
            if result:
                self.current_run_id = result[0]
            else:
                self.current_run_id = 1
        except:
            self.current_run_id = 1
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"Registered master node: {self.master_id[:8]} ({self.hostname}) - Run {self.current_run_id}")
    
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
            asyncio.create_task(self.job_creator_loop()),
            asyncio.create_task(self.health_monitor_loop())
        ]
        
        print("Master node online")
        print("Monitoring nodes and jobs...")
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.running = False
        finally:
            # Mark master as offline
            try:
                conn = self.get_db()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE nodes SET status = 'offline' WHERE id = %s",
                    (self.master_id,)
                )
                conn.commit()
                cur.close()
                conn.close()
                print(f"✅ Master node {self.hostname} marked offline")
            except Exception as e:
                print(f"Error during cleanup: {e}")
    
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
    
    async def job_creator_loop(self):
        """Create jobs based on configuration - nodes pull work themselves"""
        jobs_created = False
        
        while self.running:
            conn = self.get_db()
            cur = conn.cursor()
            
            # Get job creation config
            job_config = self.config_manager.get("job_creation", {})
            total_conversations = job_config.get("total_conversations", 100)
            conversations_per_job = job_config.get("conversations_per_job", 10)
            pending_queue_size = job_config.get("pending_queue_size", 5)
            check_interval = job_config.get("check_interval", 30)
            
            # Calculate total jobs needed
            total_jobs_needed = (total_conversations + conversations_per_job - 1) // conversations_per_job
            
            # Count existing jobs
            cur.execute("SELECT COUNT(*) FROM jobs")
            total_jobs_created = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM jobs WHERE status = 'pending'")
            pending_count = cur.fetchone()[0]
            
            # Create initial batch of jobs if none exist
            if not jobs_created and total_jobs_created == 0:
                print(f"Creating {total_jobs_needed} jobs ({total_conversations} conversations, {conversations_per_job} per job)")
                
                # Get scenarios
                cur.execute("SELECT id, name FROM scenarios")
                scenarios = cur.fetchall()
                
                if not scenarios:
                    print("No scenarios found, creating default scenario")
                    scenario_id = str(uuid.uuid4())
                    cur.execute(
                        "INSERT INTO scenarios (id, name, template) VALUES (%s, %s, %s)",
                        (scenario_id, "Healthcare Appointment Scheduling", "Generate a realistic healthcare appointment conversation")
                    )
                    scenarios = [(scenario_id, "Healthcare Appointment Scheduling")]
                
                # Create jobs
                for i in range(total_jobs_needed):
                    scenario_id, scenario_name = scenarios[i % len(scenarios)]
                    job_id = str(uuid.uuid4())
                    
                    job_params = {
                        "conversations_per_job": conversations_per_job,
                        "min_turns": 20,
                        "max_turns": 40,
                        "run_id": self.current_run_id
                    }
                    
                    cur.execute(
                        "INSERT INTO jobs (id, scenario_id, status, parameters) VALUES (%s, %s, 'pending', %s)",
                        (job_id, scenario_id, json.dumps(job_params))
                    )
                    self.jobs_created += 1
                
                self.target_jobs = total_jobs_needed
                jobs_created = True
                print(f"Created {total_jobs_needed} jobs for Run {self.current_run_id}")
            
            # Maintain pending queue size
            elif pending_count < pending_queue_size and total_jobs_created < total_jobs_needed:
                jobs_to_create = min(pending_queue_size - pending_count, total_jobs_needed - total_jobs_created)
                
                cur.execute("SELECT id, name FROM scenarios LIMIT 1")
                scenario = cur.fetchone()
                
                if scenario:
                    scenario_id, scenario_name = scenario
                    
                    for _ in range(jobs_to_create):
                        job_id = str(uuid.uuid4())
                        job_params = {
                            "conversations_per_job": conversations_per_job,
                            "min_turns": 20,
                            "max_turns": 40
                        }
                        
                        cur.execute(
                            "INSERT INTO jobs (id, scenario_id, status, parameters) VALUES (%s, %s, 'pending', %s)",
                            (job_id, scenario_id, json.dumps(job_params))
                        )
                    
                    print(f"Added {jobs_to_create} jobs to queue")
            
            conn.commit()
            cur.close()
            conn.close()
            
            await asyncio.sleep(check_interval)
    
    async def health_monitor_loop(self):
        """Comprehensive system health monitoring"""
        health_config = self.config_manager.get("health_monitor", {})
        check_interval = health_config.get("check_interval", 60)
        node_timeout = health_config.get("node_timeout", 300)
        
        while self.running:
            conn = self.get_db()
            cur = conn.cursor()
            
            # Get comprehensive system stats
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
            
            # Check if all jobs completed - shutdown orchestrator
            if self.target_jobs > 0 and completed_count >= self.target_jobs:
                print(f"\n🏁 All {self.target_jobs} jobs completed! Run {self.current_run_id} finished.")
                print(f"Generated {conv_count} total conversations. Shutting down orchestrator.")
                self.running = False
                return
            
            # Debug: Check what nodes and jobs we have
            cur.execute("SELECT hostname, node_type, status FROM nodes")
            all_nodes = cur.fetchall()
            print(f"[DEBUG] All nodes: {all_nodes}")
            
            cur.execute("SELECT COUNT(*), status FROM jobs GROUP BY status")
            job_status = cur.fetchall()
            print(f"[DEBUG] Job status counts: {job_status}")
            
            cur.execute("SELECT assigned_node_id, COUNT(*) FROM jobs WHERE status = 'completed' GROUP BY assigned_node_id")
            completed_by_node = cur.fetchall()
            print(f"[DEBUG] Completed jobs by node: {completed_by_node}")
            
            # Clean up stale nodes first
            stale_cutoff = datetime.now() - timedelta(seconds=node_timeout)
            cur.execute(
                "UPDATE nodes SET status = 'offline' WHERE status = 'online' AND last_seen < %s",
                (stale_cutoff,)
            )
            
            # Get detailed job completion data for rate calculation
            cur.execute(
                """SELECT n.hostname, n.capabilities, n.last_seen,
                   COUNT(j.id) as jobs_completed,
                   MIN(j.completed_at) as first_completion,
                   MAX(j.completed_at) as last_completion
                   FROM nodes n
                   LEFT JOIN jobs j ON j.assigned_node_id = n.id AND j.status = 'completed' AND j.completed_at > NOW() - INTERVAL '10 minutes'
                   WHERE n.status = 'online' AND n.node_type = 'generation'
                   GROUP BY n.hostname, n.capabilities, n.last_seen"""
            )
            node_stats = cur.fetchall()
            print(f"[DEBUG] Node stats query result: {node_stats}")
            
            # Calculate conversations rate
            cur.execute(
                "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM conversations WHERE created_at > NOW() - INTERVAL '10 minutes'"
            )
            conv_data = cur.fetchone()
            conv_count_recent, first_conv, last_conv = conv_data
            print(f"[DEBUG] Conversation data: {conv_count_recent} conversations, {first_conv} to {last_conv}")
            
            # Calculate actual rates per minute
            total_jobs_per_minute = 0
            total_conversations_per_minute = 0
            
            if conv_count_recent and first_conv and last_conv:
                time_span_minutes = max((last_conv - first_conv).total_seconds() / 60, 1)
                total_conversations_per_minute = conv_count_recent / time_span_minutes
            
            # Update node performance tracking
            for hostname, capabilities, last_seen, jobs_completed, first_completion, last_completion in node_stats:
                if hostname not in self.nodes:
                    self.nodes[hostname] = {}
                
                # Calculate jobs per minute for this node
                jobs_per_minute = 0
                if jobs_completed and first_completion and last_completion:
                    time_span_minutes = max((last_completion - first_completion).total_seconds() / 60, 1)
                    jobs_per_minute = jobs_completed / time_span_minutes
                
                total_jobs_per_minute += jobs_per_minute
                
                self.nodes[hostname].update({
                    'last_seen': last_seen,
                    'capabilities': capabilities if isinstance(capabilities, list) else (json.loads(capabilities) if capabilities else []),
                    'jobs_per_minute': round(jobs_per_minute, 1),
                    'jobs_completed': jobs_completed,
                    'status': 'healthy' if (datetime.now() - last_seen).seconds < node_timeout else 'stale'
                })
            
            # Calculate system efficiency
            avg_jobs_per_node = total_jobs_per_minute / max(nodes_count, 1)
            
            stats = {
                'nodes': nodes_count,
                'pending_jobs': pending_count,
                'running_jobs': running_count,
                'completed_jobs': completed_count,
                'conversations': conv_count,
                'conversations_per_minute': round(total_conversations_per_minute, 1),
                'total_jobs_per_minute': round(total_jobs_per_minute, 1),
                'avg_jobs_per_node': round(avg_jobs_per_node, 1)
            }
            
            print(f"Health: {stats['nodes']} nodes, {stats['pending_jobs']} pending, {stats['running_jobs']} running, {stats['completed_jobs']}/{self.target_jobs} completed, {stats['conversations']} conversations, {stats['conversations_per_minute']}/min (Run {self.current_run_id})")
            
            # Log node performance
            for hostname, node_data in self.nodes.items():
                status = node_data.get('status', 'unknown')
                jobs_per_minute = node_data.get('jobs_per_minute', 0)
                jobs_completed = node_data.get('jobs_completed', 0)
                print(f"  Node {hostname}: {status}, {jobs_per_minute}/min ({jobs_completed} jobs completed)")
            
            cur.close()
            conn.close()
            await asyncio.sleep(check_interval)
    
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
            
            await asyncio.sleep(self.failover_timeout // 3)
    
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
        
        # Add run_id to job parameters
        job_params = parameters or {}
        job_params['run_id'] = self.current_run_id or 1
        
        cur.execute(
            "INSERT INTO jobs (id, scenario_id, parameters) VALUES (%s, %s, %s)",
            (job_id, scenario[0], json.dumps(job_params))
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"Created job: {job_id}")
        return job_id

async def main():
    """Main entry point"""
    orchestrator = MasterOrchestrator()
    await orchestrator.start()

if __name__ == "__main__":
    asyncio.run(main())