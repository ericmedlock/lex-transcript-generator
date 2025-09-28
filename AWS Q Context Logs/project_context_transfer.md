# LLM Transcript Generation Platform

## Core System
**Path**: `C:\Users\ericm\PycharmProjects\lex-transcript-generator\`  
**DB**: PostgreSQL (EPM_DELL:5432/calllab)  
**Architecture**: Model bakeoff → hash deduplication → OpenAI grading → CSV output  
**Target**: 1000 conversations (10/job, 100 jobs)  
**Master**: EPM_DELL preferred, `config/config.json` main config  

## Key Files
- `src/master/orchestrator.py` - Job creation, health monitoring, signal handling
- `src/nodes/generation_node.py` - LLM worker, activity throttling, fixed logging bug
- `scripts/model_bakeoff_with_dedupe.py` - Model testing with OpenAI grading
- `src/core/dedupe_manager.py` - Hash-only deduplication (semantic too strict)
- `scripts/health_check.py` / `scripts/status.py` - System validation

## Configuration
**Main**: `config/config.json` (machine_name: EPM_DELL, debug_mode, models_filter)  
**Per-Host**: Interactive setup, auto-detection, smart defaults  
**Deduplication**: hash_only: false, similarity_threshold: 0.5 (but hash-only used)  
**Grading**: OpenAI GPT-4o-mini (realness, coherence, naturalness, overall)  

## Features
- Auto-discovery: LM Studio models, OpenAI keys, existing data
- Activity detection: Gaming mode, thermal throttling, gradual scaling
- Debug mode: models_filter for single model testing
- Quality pipeline: Generation → Deduplication → Grading → Storage
- Error recovery: Database retries, model fallbacks, graceful shutdown

## Commands
**Health**: `python scripts/health_check.py` (DB, LM Studio, configs)  
**Status**: `python scripts/status.py` (conversations, nodes, jobs)  
**Trial**: T1: `python src/master/orchestrator.py` T2: `python src/nodes/generation_node.py 1`  
**Production**: T1: orchestrator, T2+: `python src/nodes/generation_node.py`  
**Stop**: Ctrl+C (graceful shutdown)

## Recent Fixes
- Fixed generation_node.py misleading failure messages (logging bug)
- Switched to hash-only deduplication (semantic caused false duplicates)
- Added debug flow tracking, fixed indentation in error handling
- Validated with 2-job test (R=8, O=8 scores)
- Resolved blue screen issues via conservative resource management

## Notes
- Interactive config setup on first run, per-hostname tracking
- Multi-node ready, auto-recovery, debug_mode + models_filter for testing