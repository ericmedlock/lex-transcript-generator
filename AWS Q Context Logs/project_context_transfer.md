# LLM Transcript Platform - Context

**System**: PostgreSQL EPM_DELL:5432/calllab | 1000 convs (10/job) | Hash dedupe → OpenAI grade → CSV

**Core**: orchestrator.py (jobs, health), generation_node.py (LLM worker, activity throttle), dedupe_manager.py, health_check.py

**Config**: config.json (EPM_DELL master, debug_mode), per-hostname setup, OpenAI GPT-4o-mini grading (R/C/N/O)

**Pipeline**: LM Studio → generation (178.7 tok/s) → hash dedupe → OpenAI grade → CSV export

**Features**: Auto-discovery, gaming/thermal throttling, graceful shutdown, multi-node, debug testing

**Tools**: Prompt Tester (benchmarks), Three-Tier Grading (Local/Network/OpenAI), LEX Export (PII scrubbing), GUI Dashboard, Training Data Transformer (4-8x speedup), Dataset Analyzer (hierarchical classification, template generation, multi-format parsing)

**Status**: Working system with grading, dashboard, LEX export, performance optimization

**Enhanced Design**: Distributed system with RAG, multi-domain models, streaming pipeline, YouTube processing, activity detection, web dashboard

**Performance System**: `src/perf_generator.py` - threaded request pool, dynamic concurrency tuner (2-6 workers), PostgreSQL telemetry, real-time metrics (HTTP/WebSocket), retry logic, backpressure handling, CLI benchmark tool | Components: worker_pool.py, tuner.py, metrics_db.py, server.py, bench.py | Config: CONCURRENCY_MIN/MAX, TARGET_P95_MS=2500, TARGET_ERROR_RATE=0.03 | Commands: `python run_perf.py migrate|run|bench|test`

**Dataset Analyzer**: `dataset_analyzer/` - Domain→Category→Subcategory classification, multi-format parsing (JSON/CSV/TXT/XML), metadata extraction, template generation, LLM integration (OpenAI/local/Ollama), CLI interface | Components: file_scanner.py, format_detector.py, metadata_extractor.py, cli.py | Config: YAML-based, incremental processing, quality metrics | Commands: `python -m dataset_analyzer scan --input ../Training\ Datasets --output ./results` | Status: Core analysis working, LLM classification ready for implementation


# Distributed Transcript Intelligence Platform

**Features**: Master/worker architecture, thermal throttling, activity detection, multi-domain (healthcare/retail/telecom), GAN feedback loops, RAG integration, YouTube processing, Lex/Dialogflow/Rasa export, hardware auto-discovery, streaming pipeline, web dashboard, natural language queries, Pi support (llama.cpp), smart deduplication, dataset analysis & template generation

**Architecture**: Master Node (discovery, distribution, config, dashboard, database) | Generation Nodes (LLM inference, thermal monitoring, activity detection) | Processing Nodes (quality scoring, deduplication, validation, GAN)

**Structure**: `config/ src/ web/ data/ scripts/` | `core/ master/ nodes/ pipeline/ models/ api/`

**Quick Start**: Python 3.9+, PostgreSQL, Node.js | `pip install -r requirements.txt` | `cp .env.example .env` | `python scripts/migrate_db.py` | `python -m src.master.orchestrator` | `python -m src.nodes.generation_node`

**Performance**: 1,000+ conversations/hour per GPU node, 100+ per Pi | 95%+ quality validation, <5% duplicates | 50+ node cluster support, automatic failover | JWT auth, encrypted communication, PHI scrubbing