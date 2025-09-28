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
import signal
import sys
import os
import random
import time
from datetime import datetime
from pathlib import Path

class ModelManager:
    """Enhanced model discovery and management"""
    
    def __init__(self, llm_endpoint):
        self.llm_endpoint = llm_endpoint
        self.available_models = []
        self.chat_models = []
        self.last_discovery = None
        
    async def discover_models(self):
        """Robust model detection with fallbacks"""
        print(f"[MODEL] Discovering models from {self.llm_endpoint}")
        
        # Special handling for Pi with llama.cpp
        if self.llm_endpoint == "llama.cpp":
            self.available_models = ["gemma-1.1-2b-it-Q4_K_M"]
            print(f"[MODEL] Pi llama.cpp model: {self.available_models}")
        else:
            try:
                async with aiohttp.ClientSession() as session:
                    models_url = self.llm_endpoint.replace('/chat/completions', '/models')
                    async with session.get(models_url, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            self.available_models = [model["id"] for model in data.get("data", [])]
                            print(f"[MODEL] Found {len(self.available_models)} models: {self.available_models}")
                        else:
                            print(f"[MODEL] API error {resp.status}, using fallback")
                            self.available_models = ["microsoft/phi-4-mini-reasoning"]
            except Exception as e:
                print(f"[MODEL] Discovery failed: {e}, using fallback")
                self.available_models = ["microsoft/phi-4-mini-reasoning"]
        
        # Filter embedding models (skip for Pi)
        if self.llm_endpoint == "llama.cpp":
            self.chat_models = self.available_models
        else:
            self.chat_models = self._filter_chat_models()
        self.last_discovery = datetime.now()
        
        return self.chat_models
    
    def _filter_chat_models(self):
        """Filter out embedding models"""
        embedding_keywords = ['embedding', 'embed', 'bge-', 'e5-', 'nomic-embed', 'text-embedding']
        chat_models = []
        
        for model in self.available_models:
            model_lower = model.lower()
            is_embedding = any(keyword in model_lower for keyword in embedding_keywords)
            
            if not is_embedding:
                chat_models.append(model)
            else:
                print(f"[MODEL] Filtered embedding model: {model}")
        
        print(f"[MODEL] Chat models available: {chat_models}")
        return chat_models
    
    async def get_best_model(self):
        """Get best available model"""
        if not self.chat_models or not self.last_discovery:
            await self.discover_models()
        
        return self.chat_models[0] if self.chat_models else "microsoft/phi-4-mini-reasoning"
    
    async def validate_model(self, model_name):
        """Test if model is actually available"""
        try:
            async with aiohttp.ClientSession() as session:
                test_payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1
                }
                async with session.post(self.llm_endpoint, json=test_payload, timeout=5) as resp:
                    return resp.status == 200
        except:
            return False

class PromptManager:
    """Intelligent prompt generation with randomization"""
    
    def __init__(self):
        self.scenario_variations = {
            "healthcare": [
                "New patient scheduling first appointment",
                "Existing patient rescheduling appointment", 
                "Patient calling for urgent same-day appointment",
                "Patient scheduling follow-up after procedure",
                "Patient calling to cancel and reschedule"
            ],
            "retail": [
                "Customer placing new order",
                "Customer checking order status",
                "Customer requesting return/exchange",
                "Customer with product inquiry",
                "Customer with billing question"
            ]
        }
        
        self.patient_types = [
            "Elderly patient with hearing difficulties",
            "Busy working parent with limited availability", 
            "Anxious first-time patient",
            "Regular patient who knows the system",
            "Patient with insurance questions"
        ]
        
        self.complications = [
            "Insurance verification needed",
            "Specific doctor preference",
            "Transportation limitations", 
            "Work schedule conflicts",
            "Multiple family members need appointments"
        ]
    
    def generate_varied_prompt(self, base_scenario, scenario_name, min_turns=20, max_turns=40):
        """Generate randomized prompt to reduce duplicates"""
        
        # Determine scenario type
        scenario_type = "healthcare" if "healthcare" in scenario_name.lower() else "retail"
        
        # Add randomization
        if scenario_type in self.scenario_variations:
            scenario_detail = random.choice(self.scenario_variations[scenario_type])
            patient_type = random.choice(self.patient_types)
            complication = random.choice(self.complications)
            
            enhanced_prompt = f"""Generate a realistic {scenario_type} conversation with these details:

Scenario: {scenario_detail}
Customer type: {patient_type}
Complication: {complication}

Base scenario: {base_scenario}

Requirements:
- Length: {min_turns} to {max_turns} turns
- Format: alternating User: and Agent: lines
- Natural, realistic dialogue
- Include realistic hesitations and corrections
- Address the specific complication mentioned

Generate ONLY the conversation, no commentary:"""
        else:
            # Fallback to base scenario
            enhanced_prompt = f"""Generate a realistic conversation for: {scenario_name}

{base_scenario}

Requirements:
- Length: {min_turns} to {max_turns} turns
- Format: alternating User: and Agent: lines
- Natural, realistic dialogue
- Include realistic hesitations and corrections

Generate ONLY the conversation, no commentary:"""
        
        return enhanced_prompt

class GenerationNode:
    def __init__(self, llm_endpoint=None, max_jobs=None, config_path=None):
        self.hostname = socket.gethostname()
        # Detect if running on Raspberry Pi FIRST
        self.is_pi = self.detect_raspberry_pi()
        self.config = self.load_config(config_path)
        self.db_config = self.config.get("db_config", {
            'host': '192.168.68.60',
            'port': 5432,
            'database': 'calllab',
            'user': 'postgres',
            'password': 'pass'
        })
        self.llm_endpoint = llm_endpoint or self.config.get("llm_endpoint", "http://127.0.0.1:1234/v1/chat/completions")
        self.llama_model = None
        self.pi_manager = None
        if self.is_pi:
            self.init_llama_cpp()
        self.node_id = str(uuid.uuid4())
        self.hostname = socket.gethostname()
        self.running = False
        self.max_jobs = max_jobs
        self.jobs_processed = 0
        self.rag_preprocessor = self.init_rag()
        self.dedupe_manager = self.init_dedupe()
        self.grader = self.init_grader()
        self.current_run_id = None
        self.current_run_number = None
        self.model_manager = ModelManager(self.llm_endpoint)
        self.prompt_manager = PromptManager()
        self.completed_jobs = []  # Track completed jobs for grading
        self.activity_monitor = self.init_activity_monitor()
        self.setup_signal_handlers()
    
    def detect_raspberry_pi(self):
        """Detect if running on Raspberry Pi"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'BCM' in cpuinfo or 'Raspberry Pi' in cpuinfo
        except:
            return False
    
    def init_llama_cpp(self):
        """Initialize llama.cpp for Pi with auto-setup"""
        print("[PI] Initializing llama.cpp for Raspberry Pi...")
        try:
            # Import Pi startup manager
            import sys
            import os
            sys.path.append(os.path.dirname(__file__))
            from pi_startup import PiStartupManager
            
            # Setup Pi environment first
            print("[PI] Creating PiStartupManager...")
            self.pi_manager = PiStartupManager()
            print("[PI] Setting up Pi environment...")
            setup_result = self.pi_manager.setup()
            print(f"[PI] Setup result: {setup_result}")
            if not setup_result:
                print("[PI] Environment setup failed")
                self.llama_model = None
                self.pi_manager = None
                return
            
            # Import and load llama.cpp
            from llama_cpp import Llama
            model_path = self.pi_manager.get_model_path()
            
            if not model_path:
                print("[PI] No model path available")
                self.llama_model = None
                return
            
            print(f"[PI] Loading model from: {model_path}")
            
            import os
            n_cores = os.cpu_count() or 4
            self.llama_model = Llama(
                model_path=model_path, 
                n_ctx=2048, 
                verbose=False,
                n_threads=n_cores  # Use all available cores
            )
            print(f"[PI] Using {n_cores} CPU threads for inference")
            print(f"[PI] Successfully loaded llama.cpp model")
            
        except ImportError as e:
            print(f"[PI] Missing dependency: {e}")
            print("[PI] Install with: pip install llama-cpp-python")
            self.llama_model = None
            self.pi_manager = None
        except Exception as e:
            print(f"[PI] Failed to initialize llama.cpp: {e}")
            self.llama_model = None
            self.pi_manager = None
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def validate_startup(self):
        """Validate all connections and dependencies"""
        # Test database connection
        conn = self.get_db()
        conn.close()
        print("[NODE] Database connection OK")
        
        # Test LLM endpoint
        try:
            models = await self.model_manager.discover_models()
            if not models:
                raise Exception("No chat models available")
            print(f"[NODE] LLM endpoint OK: {len(models)} models")
        except Exception as e:
            raise Exception(f"LLM endpoint validation failed: {e}")
        
        # Test grader if enabled
        if self.grader:
            try:
                self.grader.setup_grading_schema()
                print("[NODE] Grader OK")
            except Exception as e:
                print(f"[NODE] Warning: Grader setup failed: {e}")
        
        # Test activity monitor
        if self.activity_monitor:
            mode = self.activity_monitor.get_activity_mode()
            print(f"[NODE] Activity monitor OK: {mode} mode")
    
    def load_config(self, config_path=None):
        """Load generator configuration with per-hostname support"""
        search_paths = []
        if config_path:
            search_paths.append(config_path)
        search_paths.extend([
            "node_config.json",
            "config/node_config.json"
        ])
        
        for path in search_paths:
            if Path(path).exists():
                try:
                    with open(path, 'r') as f:
                        all_configs = json.load(f)
                    
                    # Check if hostname-specific config exists
                    if self.hostname in all_configs:
                        print(f"[NODE] Loaded config for {self.hostname} from: {path}")
                        return all_configs[self.hostname]
                    else:
                        # Create interactive config for this hostname
                        print(f"[NODE] No config found for {self.hostname}, creating new config...")
                        new_config = self.create_interactive_config()
                        all_configs[self.hostname] = new_config
                        
                        # Save updated config
                        with open(path, 'w') as f:
                            json.dump(all_configs, f, indent=2)
                        
                        print(f"[NODE] Saved config for {self.hostname}")
                        return new_config
                        
                except Exception as e:
                    print(f"[NODE] Error loading {path}: {e}")
                    continue
        
        # No config file exists, create new one
        print(f"[NODE] No config file found, creating new config for {self.hostname}...")
        new_config = self.create_interactive_config()
        config_data = {self.hostname: new_config}
        
        # Save to default location
        Path("config").mkdir(exist_ok=True)
        with open("config/node_config.json", 'w') as f:
            json.dump(config_data, f, indent=2)
        
        return new_config
    
    def create_interactive_config(self):
        """Create configuration interactively"""
        defaults = {
            "db_config": {
                "host": "192.168.68.60",
                "port": 5432,
                "database": "calllab",
                "user": "postgres",
                "password": "pass"
            },
            "llm_endpoint": "http://127.0.0.1:1234/v1/chat/completions",
            "generation": {
                "temperature": 0.9,
                "max_tokens": 2000,
                "timeout": 60,
                "max_retries": 3
            },
            "rag": {
                "enabled": True,
                "search_limit": 3
            },
            "deduplication": {
                "enabled": True,
                "similarity_threshold": 0.85
            },
            "grading": {
                "enabled": True,
                "openai_api_key": ""
            },
            "resource_management": {
                "activity_detection": True,
                "thermal_throttling": True
            }
        }
        
        config = {}
        
        print(f"\nConfiguring node: {self.hostname}")
        print("Press Enter to accept defaults, or type new value:\n")
        
        # Database config
        config["db_config"] = {}
        config["db_config"]["host"] = input(f"Database host [{defaults['db_config']['host']}]: ") or defaults["db_config"]["host"]
        config["db_config"]["port"] = int(input(f"Database port [{defaults['db_config']['port']}]: ") or defaults["db_config"]["port"])
        config["db_config"]["database"] = input(f"Database name [{defaults['db_config']['database']}]: ") or defaults["db_config"]["database"]
        config["db_config"]["user"] = input(f"Database user [{defaults['db_config']['user']}]: ") or defaults["db_config"]["user"]
        config["db_config"]["password"] = input(f"Database password [{defaults['db_config']['password']}]: ") or defaults["db_config"]["password"]
        
        # LLM endpoint - skip for Pi, use llama.cpp
        if self.is_pi:
            config["llm_endpoint"] = "llama.cpp"
            print(f"Pi detected - using llama.cpp for local inference")
        else:
            config["llm_endpoint"] = input(f"LLM endpoint [{defaults['llm_endpoint']}]: ") or defaults["llm_endpoint"]
        
        # Generation settings
        config["generation"] = {}
        config["generation"]["temperature"] = float(input(f"LLM creativity (0.1=focused, 1.0=creative) [{defaults['generation']['temperature']}]: ") or defaults["generation"]["temperature"])
        config["generation"]["max_tokens"] = int(input(f"Max response length in tokens [{defaults['generation']['max_tokens']}]: ") or defaults["generation"]["max_tokens"])
        
        # Feature toggles - check if we have existing conversations for RAG
        try:
            import psycopg2
            temp_conn = psycopg2.connect(**config["db_config"])
            cur = temp_conn.cursor()
            cur.execute("SELECT COUNT(*) FROM conversations LIMIT 1")
            has_conversations = cur.fetchone()[0] > 0
            cur.close()
            temp_conn.close()
            rag_default = "Y/n" if has_conversations else "Y/n"
            rag_prompt = f"Use existing conversations as examples [{rag_default}]: "
            config["rag"] = {"enabled": input(rag_prompt).lower() != 'n'}
        except:
            config["rag"] = {"enabled": input(f"Use existing conversations as examples [Y/n]: ").lower() != 'n'}
        config["deduplication"] = {
            "enabled": input(f"Check for duplicate conversations [Y/n]: ").lower() != 'n',
            "hash_only": input(f"Fast duplicate check (hash-only, recommended) [Y/n]: ").lower() != 'n'
        }
        # Check for OpenAI key in environment
        openai_key = os.environ.get('OPENAI_API_KEY', '')
        if openai_key:
            print(f"Found OpenAI API key in environment")
            grading_enabled = input(f"Grade conversations with OpenAI [Y/n]: ").lower() != 'n'
        else:
            grading_enabled = input(f"Grade conversations with OpenAI (requires API key) [Y/n]: ").lower() != 'n'
            if grading_enabled:
                openai_key = input(f"OpenAI API key: ").strip()
        
        config["grading"] = {
            "enabled": grading_enabled,
            "openai_api_key": openai_key
        }
        config["resource_management"] = {"activity_detection": input(f"Monitor system usage and throttle when busy [Y/n]: ").lower() != 'n'}
        
        return config
        
    def get_db(self, retries=3):
        """Get database connection with retry logic"""
        for attempt in range(retries):
            try:
                return psycopg2.connect(**self.db_config)
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                print(f"[NODE] Database connection failed (attempt {attempt + 1}/{retries}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def init_rag(self):
        """Initialize RAG preprocessor"""
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data'))
            from rag_preprocessor import RAGPreprocessor
            return RAGPreprocessor()
        except Exception as e:
            print(f"Warning: RAG not available: {e}")
            return None
    
    def init_dedupe(self):
        """Initialize deduplication manager"""
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
            from dedupe_manager import DedupeManager
            return DedupeManager(db_config=self.db_config)
        except Exception as e:
            print(f"Warning: Deduplication not available: {e}")
            return None
    
    def init_grader(self):
        """Initialize conversation grader"""
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
            from conversation_grader import ConversationGrader
            return ConversationGrader(db_config=self.db_config)
        except Exception as e:
            print(f"Warning: Grader not available: {e}")
            return None
    
    def init_activity_monitor(self):
        """Initialize activity monitor"""
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
            from activity_monitor import ActivityMonitor
            return ActivityMonitor(self.config)
        except Exception as e:
            print(f"Warning: Activity monitor not available: {e}")
            return None
    
    def get_or_create_run(self):
        """Get current deduplication run"""
        if not self.dedupe_manager:
            return None, None
        
        if not self.current_run_id:
            self.current_run_id, self.current_run_number = self.dedupe_manager.get_or_create_run(
                target_conversations=1000,  # Default target
                similarity_threshold=0.85
            )
            print(f"Using deduplication run: {self.current_run_number}")
        
        return self.current_run_id, self.current_run_number
    
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
        """Start the generation node with validation"""
        print("Starting Generation Node")
        
        # Validate configuration and connections
        try:
            await self.validate_startup()
        except Exception as e:
            print(f"❌ Startup validation failed: {e}")
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
        """Pull and process available jobs with timeout"""
        last_job_time = time.time()
        timeout_minutes = 10
        
        while self.running:
            conn = self.get_db()
            cur = conn.cursor()
            
            # Atomically claim next available job with randomization to prevent hogging
            cur.execute(
                """UPDATE jobs SET status = 'running', assigned_node_id = %s, started_at = %s 
                   WHERE id = (SELECT id FROM jobs WHERE status = 'pending' ORDER BY RANDOM() LIMIT 1) 
                   RETURNING id, scenario_id, parameters""",
                (self.node_id, datetime.now())
            )
            job = cur.fetchone()
            
            if job:
                job_id, scenario_id, parameters = job
                params = parameters if isinstance(parameters, dict) else json.loads(parameters or "{}")
                last_job_time = time.time()  # Reset timeout
                
                print(f"Claimed job: {job_id[:8]}")
                
                try:
                    # Get conversations per job from parameters
                    conversations_per_job = params.get("conversations_per_job", 1)
                    
                    # Generate multiple conversations for this job
                    conversations_generated = 0
                    for conv_num in range(conversations_per_job):
                        print(f"[DEBUG] Generating conversation {conv_num+1}/{conversations_per_job} for job {job_id[:8]}")
                        conversation = await self.generate_conversation(scenario_id, params)
                        
                        if conversation:
                            # Extract metadata
                            metadata = conversation.pop("_metadata", {})
                            
                            # Check for duplicates if deduplication enabled
                            run_id, run_number = self.get_or_create_run()
                            is_duplicate = False
                            duplicate_reason = "unique"
                            
                            if self.dedupe_manager and run_number:
                                is_duplicate, duplicate_reason = self.dedupe_manager.is_duplicate(
                                    run_number, conversation, self.hostname, model_name=metadata.get("model_name")
                                )
                            
                            if is_duplicate:
                                print(f"[DEBUG] Duplicate detected ({duplicate_reason}), retrying conversation {conv_num+1}/{conversations_per_job}")
                                continue  # Try next conversation
                            else:
                                # Save unique conversation
                                conv_id = str(uuid.uuid4())
                                # Store performance metrics
                                perf_metrics = {
                                    "realness_score": None,
                                    "speed_score": metadata.get("tokens_per_sec", 0),
                                    "gan_score": None,
                                    "duplicate_status": duplicate_reason,
                                    "completion_tokens": metadata.get("completion_tokens", 0),
                                    "rag_used": metadata.get("rag_examples_used", False),
                                    "retry_attempt": metadata.get("attempt", 1)
                                }
                                
                                # Get run_id from job parameters
                                run_id = params.get('run_id', 1)
                                
                                cur.execute(
                                    """INSERT INTO conversations 
                                       (id, job_id, scenario_id, content, quality_score, model_name, 
                                        generation_start_time, generation_end_time, generation_duration_ms, 
                                        evaluation_metrics, run_id) 
                                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                    (conv_id, job_id, scenario_id, json.dumps(conversation), 0.8,
                                     metadata.get("model_name"), metadata.get("start_time"), 
                                     metadata.get("end_time"), metadata.get("duration_ms"), 
                                     json.dumps(perf_metrics), run_id)
                                )
                                
                                # Track completed conversation for grading
                                self.completed_jobs.append(conv_id)
                                conversations_generated += 1
                                
                                tokens_per_sec = metadata.get("tokens_per_sec", 0)
                                print(f"[DEBUG] Generated conversation {conversations_generated}/{conversations_per_job} for job {job_id[:8]} ({tokens_per_sec:.1f} tok/s)")
                        else:
                            print(f"[DEBUG] Failed to generate conversation {conv_num+1}/{conversations_per_job} - conversation is None")
                    
                    # Mark job complete after all conversations generated
                    cur.execute(
                        "UPDATE jobs SET status = 'completed', completed_at = %s WHERE id = %s",
                        (datetime.now(), job_id)
                    )
                    
                    print(f"Completed job: {job_id[:8]} -> {conversations_generated} conversations")
                    
                    # Check if we've hit the job limit
                    self.jobs_processed += 1
                    if self.max_jobs and self.jobs_processed >= self.max_jobs:
                        print(f"Reached job limit ({self.max_jobs}), starting grading phase...")
                        await self.grade_completed_conversations()
                        self.running = False
                        return
                    
                    # If no conversations generated, mark job as failed
                    if conversations_generated == 0:
                        cur.execute(
                            "UPDATE jobs SET status = 'failed' WHERE id = %s", (job_id,)
                        )
                        print(f"Failed job: {job_id[:8]} - no conversations generated")
                
                except Exception as e:
                    print(f"Error processing job {job_id[:8]}: {e}")
                    cur.execute(
                        "UPDATE jobs SET status = 'failed' WHERE id = %s", (job_id,)
                    )
                
                conn.commit()
            else:
                # Check timeout - no jobs for 10 minutes
                if time.time() - last_job_time > (timeout_minutes * 60):
                    print(f"⏰ No jobs available for {timeout_minutes} minutes. Shutting down gracefully.")
                    self.running = False
                    break
                
                # No jobs available, wait briefly
                await asyncio.sleep(2)
                continue
            
            cur.close()
            conn.close()
            await asyncio.sleep(0.1)  # Very brief pause between jobs
    
    async def get_available_model(self):
        """Get best available model using ModelManager"""
        return await self.model_manager.get_best_model()
    
    async def generate_conversation(self, scenario_id, parameters):
        """Generate a conversation using LLM with retry logic and performance tracking"""
        # Check activity and throttle if needed
        if self.activity_monitor:
            mode = self.activity_monitor.get_activity_mode()
            throttle_factor = self.activity_monitor.get_throttle_factor()
            
            if self.activity_monitor.should_throttle():
                limits = self.activity_monitor.get_resource_limits()
                print(f"Throttling due to {mode} (factor: {throttle_factor:.1f}), waiting {limits.get('delay', 5)}s...")
                await asyncio.sleep(limits.get('delay', 5))
            elif throttle_factor < 1.0:
                # Gradual scaling - add small delay for non-idle modes
                delay = int((1.0 - throttle_factor) * 5)  # 0-5 second delay
                if delay > 0:
                    await asyncio.sleep(delay)
        
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
        
        # Get and validate model
        model_name = await self.get_available_model()
        if not await self.model_manager.validate_model(model_name):
            print(f"Model {model_name} not available, trying alternatives...")
            await self.model_manager.discover_models()
            model_name = await self.get_available_model()
        
        # Search for similar conversations
        rag_config = self.config.get("rag", {})
        if rag_config.get("enabled", True):
            search_limit = rag_config.get("search_limit", 3)
            rag_examples = self.rag_search(f"{scenario_name} {template}", limit=search_limit)
        else:
            rag_examples = ""
        
        # Generate varied prompt using PromptManager
        base_prompt = self.prompt_manager.generate_varied_prompt(
            template, scenario_name, min_turns, max_turns
        )
        
        # Enhance with RAG examples if available
        if rag_examples:
            prompt = f"""Based on these real conversation examples:

{rag_examples}

Now generate a conversation using this guidance:

{base_prompt}"""
        else:
            prompt = base_prompt
        
        # Get generation config
        gen_config = self.config.get("generation", {})
        temperature = gen_config.get("temperature", 0.9)
        max_tokens = gen_config.get("max_tokens", 2000)
        timeout = gen_config.get("timeout", 60)
        max_retries = gen_config.get("max_retries", 3)
        
        # Retry logic for LLM calls
        for attempt in range(max_retries):
            start_time = datetime.now()
            
            try:
                # Use llama.cpp direct calls for Pi, HTTP for others
                if self.is_pi and self.llama_model:
                    # Direct llama.cpp call
                    try:
                        response = self.llama_model(prompt, max_tokens=max_tokens, temperature=temperature)
                        end_time = datetime.now()
                        duration_ms = int((end_time - start_time).total_seconds() * 1000)
                        
                        text = response['choices'][0]['text']
                        print(f"[DEBUG] Pi LLM response: {len(text)} chars")
                        
                        # Calculate performance metrics
                        completion_tokens = len(text.split())
                        tokens_per_sec = completion_tokens / (duration_ms / 1000) if duration_ms > 0 else 0
                        
                        # Convert to Contact Lens format and add metadata
                        conversation = self.format_conversation(text, scenario_name)
                        conversation["_metadata"] = {
                            "model_name": "llama.cpp",
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat(),
                            "duration_ms": duration_ms,
                            "completion_tokens": completion_tokens,
                            "tokens_per_sec": tokens_per_sec,
                            "rag_examples_used": bool(rag_examples),
                            "attempt": attempt + 1
                        }
                        
                        return conversation
                    except Exception as e:
                        print(f"[DEBUG] Pi LLM error: {e}")
                        if attempt == max_retries - 1:
                            return None
                elif self.is_pi:
                    # Pi without loaded model - fail fast
                    print(f"[DEBUG] Pi detected but no llama model loaded")
                    return None
                else:
                    # LM Studio HTTP format
                    payload = {
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(self.llm_endpoint, json=payload, timeout=timeout) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                end_time = datetime.now()
                                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                                print(f"[DEBUG] LLM response received: {len(text)} chars, model: {model_name}")
                                
                                # Calculate performance metrics
                                usage = data.get("usage", {})
                                completion_tokens = usage.get("completion_tokens", len(text.split()))
                                tokens_per_sec = completion_tokens / (duration_ms / 1000) if duration_ms > 0 else 0
                                
                                # Convert to Contact Lens format and add metadata
                                conversation = self.format_conversation(text, scenario_name)
                                conversation["_metadata"] = {
                                    "model_name": model_name,
                                    "start_time": start_time.isoformat(),
                                    "end_time": end_time.isoformat(),
                                    "duration_ms": duration_ms,
                                    "completion_tokens": completion_tokens,
                                    "tokens_per_sec": tokens_per_sec,
                                    "rag_examples_used": bool(rag_examples),
                                    "attempt": attempt + 1
                                }
                                
                                return conversation
                            else:
                                error_text = await resp.text()
                                end_time = datetime.now()
                                print(f"[DEBUG] LLM API error: {resp.status} - {error_text[:200]} (attempt {attempt + 1}/{max_retries})")
                                if attempt == max_retries - 1:
                                    return None
            
            except Exception as e:
                print(f"[DEBUG] LLM call exception: {type(e).__name__}: {e} (attempt {attempt + 1}/{max_retries})")
                import traceback
                print(f"[DEBUG] Traceback: {traceback.format_exc()[:500]}")
                if attempt == max_retries - 1:
                    return None
                
                # Wait before retry
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
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
    
    async def grade_completed_conversations(self):
        """Grade conversations completed by this node"""
        if not self.grader or not self.completed_jobs:
            print("No grader available or no conversations to grade")
            return
        
        print(f"Grading {len(self.completed_jobs)} completed conversations...")
        
        # Setup grading schema if needed
        try:
            self.grader.setup_grading_schema()
        except Exception as e:
            print(f"Warning: Could not setup grading schema: {e}")
        
        # Grade conversations by this machine
        graded_count = self.grader.grade_database_conversations(
            machine_name=self.hostname,
            limit=len(self.completed_jobs)
        )
        
        print(f"Graded {graded_count} conversations")
    
    async def shutdown(self):
        """Shutdown the node"""
        # Grade any remaining conversations before shutdown
        await self.grade_completed_conversations()
        
        # Pi cleanup
        if self.is_pi and hasattr(self, 'pi_manager') and self.pi_manager:
            self.pi_manager.teardown()
        
        self.running = False

if __name__ == "__main__":
    import sys
    max_jobs = int(sys.argv[1]) if len(sys.argv) > 1 else None
    node = GenerationNode(max_jobs=max_jobs)
    asyncio.run(node.start())