-- Add run_id to conversations table and set existing data to run 1
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS run_id INTEGER DEFAULT 1;

-- Update existing conversations to run 1
UPDATE conversations SET run_id = 1 WHERE run_id IS NULL;

-- Create index for run_id queries
CREATE INDEX IF NOT EXISTS idx_conversations_run_id ON conversations(run_id);

-- Create run_counter table to track current run
CREATE TABLE IF NOT EXISTS run_counter (
    id INTEGER PRIMARY KEY DEFAULT 1,
    current_run INTEGER DEFAULT 1,
    CONSTRAINT single_row CHECK (id = 1)
);

-- Insert initial run counter
INSERT INTO run_counter (id, current_run) VALUES (1, 1) ON CONFLICT (id) DO NOTHING;