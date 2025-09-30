SELECT 
    c.id as conversation_id,
    c.model_name,
    c.quality_score,
    c.generation_start_time,
    c.generation_end_time,
    c.generation_duration_ms,
    c.created_at,
    
    -- Extract performance metrics from JSON
    c.evaluation_metrics->>'speed_score' as speed_score,
    c.evaluation_metrics->>'duplicate_status' as duplicate_status,
    c.evaluation_metrics->>'completion_tokens' as completion_tokens,
    c.evaluation_metrics->>'rag_used' as rag_used,
    c.evaluation_metrics->>'retry_attempt' as retry_attempt,
    
    -- Job and scenario info
    j.id as job_id,
    j.status as job_status,
    j.started_at as job_started,
    j.completed_at as job_completed,
    s.name as scenario_name,
    
    -- Node info
    n.hostname as machine_name,
    n.capabilities,
    
    -- Grading data
    g.realness_score as graded_realness,
    g.coherence_score as graded_coherence,
    g.naturalness_score as graded_naturalness,
    g.overall_score as graded_overall,
    g.brief_feedback,
    g.graded_at,
    
    -- Calculate tokens per second
    CASE 
        WHEN c.generation_duration_ms > 0 AND c.evaluation_metrics->>'completion_tokens' IS NOT NULL
        THEN (c.evaluation_metrics->>'completion_tokens')::float / (c.generation_duration_ms::float / 1000)
        ELSE NULL
    END as tokens_per_second,
    
    -- Extract processing type
    CASE 
        WHEN n.capabilities::text LIKE '%gpu%' THEN 'GPU'
        ELSE 'CPU'
    END as processing_type
    
FROM conversations c
LEFT JOIN jobs j ON c.job_id = j.id
LEFT JOIN scenarios s ON c.scenario_id = s.id
LEFT JOIN nodes n ON j.assigned_node_id = n.id
LEFT JOIN conversation_grades g ON c.id = g.conversation_id

ORDER BY c.created_at DESC;