# LLM Transcript Platform - Consolidated Context

## System Overview
**Core System**: PostgreSQL EPM_DELL:5432/calllab | Distributed transcript generation with master/worker architecture | Hash dedupe → OpenAI grade → CSV/LEX export

**Architecture**: Master Node (orchestration, job distribution, health monitoring, web dashboard, database) | Generation Nodes (LLM inference, thermal monitoring, activity detection) | Processing Nodes (quality scoring, deduplication, validation, GAN feedback)

**Pipeline**: LM Studio/Ollama → generation (178.7 tok/s) → hash dedupe → OpenAI grade (R/C/N/O) → CSV/LEX export with PII scrubbing

## Core Components
**Master**: orchestrator.py (jobs, health, node discovery), work_distributor.py (intelligent load balancing), config_manager.py (database-first config)

**Generation**: generation_node.py (LLM worker, activity throttle, thermal management), supports Pi 4/5 nodes with llama.cpp

**Processing**: dedupe_manager.py (hash/semantic), quality_engine.py (GAN-style scoring), health_check.py

**Config**: config.json (EPM_DELL master, debug_mode), per-hostname setup, node profiles (master/generation/processing/pi)

## Features & Tools
**Core Features**: Auto-discovery, gaming/thermal throttling, graceful shutdown, multi-node scaling, debug testing, streaming pipeline, YouTube processing, activity detection, web dashboard, natural language queries

**Advanced Tools**: 
- **Prompt Tester**: Benchmarks and performance testing
- **Three-Tier Grading**: Local/Network/OpenAI with GUI radio buttons
- **LEX Export**: PII scrubbing for Amazon Lex Contact Lens v1.1.0
- **GUI Dashboard**: Real-time monitoring, job management, result visualization
- **Training Data Transformer**: 4-8x speedup optimization
- **Dataset Analyzer**: Hierarchical classification (Domain→Category→Subcategory), template generation, multi-format parsing (JSON/CSV/TXT/XML), metadata extraction, LLM integration (OpenAI/local/Ollama)
- **Model Bakeoff**: Multi-model benchmarking with system detection, CSV reporting, VRAM management

## Performance & Scale
**Performance System**: `src/perf_generator.py` - threaded request pool, dynamic concurrency tuner (2-6 workers), PostgreSQL telemetry, real-time metrics (HTTP/WebSocket), retry logic, backpressure handling, CLI benchmark tool

**Components**: worker_pool.py, tuner.py, metrics_db.py, server.py, bench.py

**Config**: CONCURRENCY_MIN/MAX, TARGET_P95_MS=2500, TARGET_ERROR_RATE=0.03

**Commands**: `python run_perf.py migrate|run|bench|test`

**Scale**: 1,000+ conversations/hour per GPU node, 100+ per Pi | 95%+ quality validation, <5% duplicates | 50+ node cluster support, automatic failover | JWT auth, encrypted communication, PHI scrubbing

## AI-Catalyst Framework Integration
**Status**: Refactored from local directory to pip-installed package | Issue: Broken imports in pip package (missing engine.py) | Workaround: Try/catch blocks with fallback error handling in conversation_grader.py, training_dataset_processor.py | Working with graceful degradation

**Framework Components**: LLM Provider (three-tier system), PII Detection & Scrubbing, File Processing (async streaming), Security Components (encryption, key vault, rate limiting, audit logging), Resilience Patterns (retry, circuit breaker, health checker)

**Architecture**: Async-first design, zero-trust security model, performance optimizations (concurrent processing, streaming, connection pooling)

## Unit Test Suite
**Testing Framework**: `unit-tests/` - Comprehensive async testing framework with GUI frontend | 27 test cases across 4 suites (core, data, integration) 

**Components**: test_framework.py (TestRunner/TestCase/TestSuite), gui/test_runner_gui.py (Tkinter interface), run_tests.py (CLI/GUI entry)

**Features**: Real-time monitoring, progress bars, result visualization, JSON export/import, mock implementations for offline testing

**Commands**: `python unit-tests/run_tests.py` (GUI) or `python unit-tests/run_tests.py --cli`

**Status**: Production-ready with cross-platform compatibility

**Coverage**: Core components (ConfigManager, Database), Data processing (PIIProcessor), AI-Catalyst integration with mocks | Test types: Unit, integration, performance, edge cases

## Data Processing & Analysis
**Dataset Analyzer**: `dataset_analyzer/` - Domain→Category→Subcategory classification, multi-format parsing (JSON/CSV/TXT/XML), metadata extraction, template generation, LLM integration (OpenAI/local/Ollama), CLI interface

**Components**: file_scanner.py, format_detector.py, metadata_extractor.py, cli.py

**Config**: YAML-based, incremental processing, quality metrics

**Commands**: `python -m dataset_analyzer scan --input ../Training\ Datasets --output ./results`

**Status**: Core analysis working, LLM classification ready for implementation

**Data Sources**: Kaggle/HuggingFace datasets, YouTube audio processing (yt-dlp, Whisper, speaker diarization), multi-format ingestion

**Processing Pipeline**: Format detection → quality filtering → topic classification → speaker analysis → deduplication → normalization → augmentation → validation

## Database & Configuration
**Database**: PostgreSQL EPM_DELL:5432/calllab with pgvector for embeddings | Tables: nodes, models, scenarios, jobs, conversations, quality_scores

**Schema**: UUID primary keys, JSONB metadata, vector embeddings, time-series metrics, audit logging

**Config Management**: Database-first with YAML fallbacks, per-node profiles, hot reloading, environment-aware deployments

**Migration**: Idempotent SQL scripts, version control, seed data, automated setup/teardown

## Media Processing
**Audio Processing**: MP4/MP3/WAV/M4A/FLAC/OGG/AAC → 16kHz WAV normalization using MoviePy/FFmpeg

**YouTube Integration**: yt-dlp extraction, multi-model transcription (Whisper variants, wav2vec2), speaker diarization, content classification

**Transcription Models**: whisper-large (highest accuracy), whisper-medium (balanced), faster-whisper (high throughput), wav2vec2 (English-only speed)

**Pipeline**: URL → audio extraction → enhancement → transcription → speaker diarization → conversation formatting → quality validation

## Quality & Intelligence
**GAN-Style Feedback**: Discriminator network for conversation scoring, pattern recognition, feedback generation, prompt evolution, scenario balancing, diversity optimization

**Quality Metrics**: Realism scores, medical accuracy, flow quality, coherence, completeness, semantic similarity detection

**Intelligent Features**: Natural language queries ("Generate 500 healthcare transcripts with frustrated female callers"), smart parameter inference, query history, batch processing

**RAG Integration**: Vector database (ChromaDB/Pinecone), conversation embeddings, topic models, speaker profiles, intent hierarchies, persistent knowledge storage

## Development Environment
**Platform**: Windows 10, Python 3.9+, PostgreSQL, Node.js for web dashboard

**Project Structure**: `c:\Users\ericm\PycharmProjects\LLM-Transcript-Data-Gen\` with "Training Datasets" (space in name)

**LLM Setup**: LM Studio on port 1234 (preferred over Ollama), currently using microsoft/phi-4-mini-reasoning model

**Hardware**: MSI laptop with RTX 4050 GPU, EPM_DELL desktop system, Pi 4/5 nodes planned

**User Preferences**: Step-by-step approach due to ADHD, minimal verbose implementations, ASCII-safe code, config-driven patterns (no hardcoding)

## Recent Developments
**Model Bakeoff System**: Automated benchmarking across multiple models with system detection (GPU model, VRAM, platform), CSV reporting, optional VRAM cleanup between models, 10 trials per model for statistical accuracy

**Batch Processing**: Parallel transcript filtering (batch_filter_calls.py) processed 739 files across 6 directories, identified 633 patient conversations (85.7%), removed 78 IVR-only files (10.6%) and 28 error files (3.8%)

**Database Migration**: Successfully migrated from SQLite to PostgreSQL with proper UUID types, JSONB columns, connection pooling, and enhanced schema for model tracking, timing data, and evaluation metrics

**Conversation Generation**: Working end-to-end pipeline with master orchestrator creating jobs, generation nodes processing via LM Studio API, storing results in PostgreSQL with metadata (model_name, generation_duration_ms, evaluation_metrics)

## Web Dashboard Design
**Planned Features**: Real-time node monitoring, job queue management, performance analytics, quality control center, configuration management, alert system, GAN feedback visualization, natural language query interface

**Technology Stack**: React/Vue.js frontend, WebSocket real-time updates, RESTful API integration, PostgreSQL direct queries, Redis caching, JWT authentication

**Monitoring**: Hardware metrics (CPU/GPU temp, utilization, memory), performance indicators (tokens/second, conversations/hour), system health (heartbeats, job status, error rates), resource usage tracking

## Status Summary
**Current State**: Working distributed system with PostgreSQL backend, LM Studio integration, quality grading, dashboard monitoring, LEX export, performance optimization, comprehensive testing framework

**Active Components**: Master orchestrator, generation nodes, database schema, model benchmarking, dataset analysis, unit testing, AI-Catalyst framework integration

**Next Priorities**: Web dashboard implementation, advanced GAN feedback loops, YouTube processing pipeline, multi-domain model specialization, intelligent resource management with activity detection