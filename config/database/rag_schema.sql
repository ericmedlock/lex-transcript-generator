-- RAG Vector Database Schema
-- Requires pgvector extension

-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Document chunks table for RAG
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_file VARCHAR(255) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768), -- Nomic embed text v1.5 embedding size
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Index for vector similarity search
    CONSTRAINT unique_chunk UNIQUE(source_file, chunk_index)
);

-- Create vector similarity index
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx 
ON document_chunks USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Full text search index
CREATE INDEX IF NOT EXISTS document_chunks_content_idx 
ON document_chunks USING gin(to_tsvector('english', content));

-- Source files tracking
CREATE TABLE IF NOT EXISTS rag_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path VARCHAR(500) NOT NULL UNIQUE,
    file_type VARCHAR(50) NOT NULL,
    total_chunks INTEGER DEFAULT 0,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);