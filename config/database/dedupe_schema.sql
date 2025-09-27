-- Deduplication System Schema
-- Manages run-specific deduplication with vector similarity

-- Run metadata table
CREATE TABLE IF NOT EXISTS dedupe_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_number INTEGER UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    target_conversations INTEGER,
    similarity_threshold FLOAT DEFAULT 0.85,
    metadata JSONB
);

-- Dynamic conversation storage per run
-- Table name format: dedupe_conversations_run_{run_number}
-- Created dynamically for each run

-- Run sequence counter
CREATE SEQUENCE IF NOT EXISTS dedupe_run_counter START 1;

-- Function to create run-specific table
CREATE OR REPLACE FUNCTION create_dedupe_table(run_num INTEGER)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS dedupe_conversations_run_%s (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_hash VARCHAR(64) UNIQUE NOT NULL,
            embedding VECTOR(768),
            content_preview TEXT,
            node_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB
        )', run_num);
    
    EXECUTE format('
        CREATE INDEX IF NOT EXISTS dedupe_conversations_run_%s_embedding_idx 
        ON dedupe_conversations_run_%s USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100)', run_num, run_num);
END;
$$ LANGUAGE plpgsql;

-- Function to check similarity in run table
CREATE OR REPLACE FUNCTION check_similarity(run_num INTEGER, check_embedding VECTOR(768), threshold FLOAT DEFAULT 0.85)
RETURNS TABLE(similar_id UUID, similarity_score FLOAT) AS $$
BEGIN
    RETURN QUERY EXECUTE format('
        SELECT id, 1 - (embedding <=> $1) as similarity
        FROM dedupe_conversations_run_%s 
        WHERE 1 - (embedding <=> $1) > $2
        ORDER BY similarity DESC
        LIMIT 1', run_num)
    USING check_embedding, threshold;
END;
$$ LANGUAGE plpgsql;