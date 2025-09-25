-- Distributed Transcript Generation System Database Schema

-- System Configuration
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    data_type VARCHAR(50) NOT NULL DEFAULT 'string',
    description TEXT,
    category VARCHAR(100),
    is_sensitive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Node Registry
CREATE TABLE nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname VARCHAR(255) NOT NULL,
    ip_address INET NOT NULL,
    node_type VARCHAR(50) NOT NULL, -- 'master', 'generation', 'processing'
    status VARCHAR(20) DEFAULT 'offline', -- 'online', 'offline', 'maintenance'
    capabilities JSONB NOT NULL DEFAULT '{}',
    hardware_info JSONB NOT NULL DEFAULT '{}',
    performance_metrics JSONB DEFAULT '{}',
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Model Registry
CREATE TABLE models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID REFERENCES nodes(id) ON DELETE CASCADE,
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100) NOT NULL, -- 'llm', 'transcription', 'classification'
    endpoint_url VARCHAR(500) NOT NULL,
    api_format VARCHAR(50) NOT NULL, -- 'openai', 'ollama', 'custom'
    capabilities JSONB DEFAULT '{}',
    performance_stats JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scenario Configuration
CREATE TABLE scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    domain VARCHAR(100) NOT NULL, -- 'healthcare', 'retail', 'telecom'
    weight DECIMAL(5,4) DEFAULT 1.0,
    complexity_level VARCHAR(20) DEFAULT 'medium', -- 'simple', 'medium', 'complex'
    template JSONB NOT NULL,
    success_rate DECIMAL(5,4) DEFAULT 0.0,
    total_generated INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Work Queue
CREATE TABLE work_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(100) NOT NULL, -- 'generation', 'processing', 'validation'
    priority INTEGER DEFAULT 50,
    payload JSONB NOT NULL,
    assigned_node_id UUID REFERENCES nodes(id),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'assigned', 'processing', 'completed', 'failed'
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Generated Conversations
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID REFERENCES scenarios(id),
    generated_by_node_id UUID REFERENCES nodes(id),
    content JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    quality_score DECIMAL(5,4),
    is_duplicate BOOLEAN DEFAULT FALSE,
    output_format VARCHAR(50) DEFAULT 'contact_lens',
    file_path VARCHAR(1000),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quality Metrics
CREATE TABLE quality_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    score DECIMAL(5,4) NOT NULL,
    details JSONB DEFAULT '{}',
    evaluated_by_node_id UUID REFERENCES nodes(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Data Sources (for RAG and training)
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'kaggle', 'huggingface', 'youtube', 'upload', 'mp4', 'mp3', 'audio'
    url VARCHAR(1000),
    file_path VARCHAR(1000),
    domain VARCHAR(100),
    total_records INTEGER DEFAULT 0,
    processed_records INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    metadata JSONB DEFAULT '{}',
    audio_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_nodes_status ON nodes(status);
CREATE INDEX idx_nodes_type ON nodes(node_type);
CREATE INDEX idx_work_queue_status ON work_queue(status);
CREATE INDEX idx_work_queue_priority ON work_queue(priority DESC);
CREATE INDEX idx_conversations_scenario ON conversations(scenario_id);
CREATE INDEX idx_conversations_quality ON conversations(quality_score DESC);
CREATE INDEX idx_system_config_category ON system_config(category);

-- Insert default system configuration
INSERT INTO system_config (key, value, data_type, description, category) VALUES
('master.max_nodes', '50', 'integer', 'Maximum number of nodes in cluster', 'cluster'),
('generation.default_batch_size', '10', 'integer', 'Default batch size for generation tasks', 'generation'),
('quality.min_score_threshold', '0.7', 'float', 'Minimum quality score to accept conversations', 'quality'),
('thermal.cpu_temp_limit', '80', 'integer', 'CPU temperature limit in Celsius', 'thermal'),
('thermal.gpu_temp_limit', '85', 'integer', 'GPU temperature limit in Celsius', 'thermal'),
('pipeline.max_queue_size', '10000', 'integer', 'Maximum items in work queue', 'pipeline'),
('api.rate_limit_per_minute', '1000', 'integer', 'API rate limit per minute', 'api');