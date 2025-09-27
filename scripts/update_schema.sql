-- Add new columns to existing conversations table
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS model_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS generation_start_time TIMESTAMP,
ADD COLUMN IF NOT EXISTS generation_end_time TIMESTAMP,
ADD COLUMN IF NOT EXISTS generation_duration_ms INTEGER,
ADD COLUMN IF NOT EXISTS evaluation_metrics JSONB;