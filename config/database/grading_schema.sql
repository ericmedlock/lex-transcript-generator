-- Conversation Grading Schema
-- Stores quality scores for generated conversations

CREATE TABLE IF NOT EXISTS conversation_grades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    realness_score INTEGER CHECK (realness_score >= 1 AND realness_score <= 10),
    coherence_score INTEGER CHECK (coherence_score >= 1 AND coherence_score <= 10),
    naturalness_score INTEGER CHECK (naturalness_score >= 1 AND naturalness_score <= 10),
    overall_score INTEGER CHECK (overall_score >= 1 AND overall_score <= 10),
    brief_feedback TEXT,
    grading_error TEXT,
    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    graded_by VARCHAR(255) DEFAULT 'openai-gpt4o-mini',
    
    -- Ensure one grade per conversation
    UNIQUE(conversation_id)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_conversation_grades_conversation_id 
ON conversation_grades(conversation_id);

-- Index for quality analysis
CREATE INDEX IF NOT EXISTS idx_conversation_grades_overall_score 
ON conversation_grades(overall_score);

-- Index for error tracking
CREATE INDEX IF NOT EXISTS idx_conversation_grades_error 
ON conversation_grades(grading_error) WHERE grading_error IS NOT NULL;

-- View for conversation analysis
CREATE OR REPLACE VIEW conversation_analysis AS
SELECT 
    c.id as conversation_id,
    c.model_name,
    c.created_at,
    n.hostname as generated_by,
    cg.realness_score,
    cg.coherence_score,
    cg.naturalness_score,
    cg.overall_score,
    cg.brief_feedback,
    cg.grading_error,
    cg.graded_at
FROM conversations c
LEFT JOIN conversation_grades cg ON cg.conversation_id = c.id
LEFT JOIN jobs j ON j.id = c.job_id
LEFT JOIN nodes n ON n.id = j.assigned_node_id;