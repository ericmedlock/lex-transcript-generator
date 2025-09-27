-- Distributed Transcript Intelligence Platform Database Schema
-- SQLite compatible, easily portable to PostgreSQL

-- Drop tables if they exist (for clean rebuilds)
DROP TABLE IF EXISTS conversations;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS models;
DROP TABLE IF EXISTS nodes;
DROP TABLE IF EXISTS scenarios;

-- Node registry - track all worker machines
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    ip_address TEXT,
    node_type TEXT NOT NULL, -- 'generation', 'processing', 'master'
    status TEXT DEFAULT 'offline', -- 'online', 'offline', 'busy'
    capabilities TEXT, -- JSON: ["gpu", "cpu", "transcription"]
    performance_score REAL DEFAULT 1.0,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- LLM model endpoints
CREATE TABLE models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    endpoint_url TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_type TEXT, -- 'generation', 'classification', 'transcription'
    status TEXT DEFAULT 'unknown', -- 'active', 'inactive', 'error'
    performance_metrics TEXT, -- JSON: {"speed": 1.2, "quality": 0.95}
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES nodes(id)
);

-- Conversation scenarios/templates
CREATE TABLE scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL, -- 'healthcare', 'retail', 'telecom'
    template TEXT NOT NULL, -- Prompt template
    weight REAL DEFAULT 1.0, -- Probability weight
    success_rate REAL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Work queue
CREATE TABLE jobs (
    id TEXT PRIMARY KEY, -- UUID
    job_type TEXT NOT NULL, -- 'generate', 'process', 'transcribe'
    status TEXT DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    assigned_node_id TEXT,
    scenario_id INTEGER,
    parameters TEXT, -- JSON: {"min_turns": 20, "max_turns": 40}
    priority INTEGER DEFAULT 5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    FOREIGN KEY (assigned_node_id) REFERENCES nodes(id),
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id)
);

-- Generated conversations
CREATE TABLE conversations (
    id TEXT PRIMARY KEY, -- UUID
    job_id TEXT NOT NULL,
    scenario_id INTEGER,
    content TEXT NOT NULL, -- JSON: Contact Lens format
    quality_score REAL,
    metadata TEXT, -- JSON: {"turns": 25, "duration": 120}
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id),
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id)
);

-- Indexes for performance
CREATE INDEX idx_nodes_status ON nodes(status);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_priority ON jobs(priority DESC);
CREATE INDEX idx_conversations_quality ON conversations(quality_score);
CREATE INDEX idx_models_node ON models(node_id);