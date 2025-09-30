-- Performance Telemetry Schema
-- Compatible with PostgreSQL and Supabase

-- Performance runs tracking
CREATE TABLE IF NOT EXISTS perf_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    model_id TEXT NOT NULL,
    host TEXT,
    notes TEXT
);

-- Performance samples (tuner metrics)
CREATE TABLE IF NOT EXISTS perf_samples (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID REFERENCES perf_runs(run_id),
    ts TIMESTAMPTZ NOT NULL,
    window_sec INT NOT NULL,
    concurrency INT NOT NULL,
    queue_depth INT NOT NULL,
    throughput_rps NUMERIC NOT NULL,
    p50_ms INT NOT NULL,
    p95_ms INT NOT NULL,
    error_rate NUMERIC NOT NULL,
    tokens_in INT NOT NULL,
    tokens_out INT NOT NULL
);

-- Individual job performance
CREATE TABLE IF NOT EXISTS perf_jobs (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID REFERENCES perf_runs(run_id),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    latency_ms INT NOT NULL,
    model_id TEXT NOT NULL,
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    http_status INT,
    error_text TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_perf_samples_run_ts ON perf_samples(run_id, ts);
CREATE INDEX IF NOT EXISTS idx_perf_jobs_run ON perf_jobs(run_id);
CREATE INDEX IF NOT EXISTS idx_perf_runs_started ON perf_runs(started_at);