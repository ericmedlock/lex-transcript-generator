# LLM Transcript Data Generation Platform - Context Transfer

## System Overview
**Base Directory**: `C:\Users\ericm\PycharmProjects\LLM-Transcript-Data-Gen\`
**Database**: PostgreSQL (EPM_DELL:5432, calllab, postgres/pass)
**Output**: Amazon Connect Contact Lens v1.1.0 JSON format
**Architecture**: Distributed master/worker nodes with per-hostname configs, graceful shutdown, interactive setup
**Target**: 1000 conversations, 10 per job (100 jobs total)

## Key Components
- **Master Orchestrator**: `src/master/orchestrator.py` - Job creation, health monitoring, EPM_DELL preference, signal handling
- **Generation Node**: `src/nodes/generation_node.py` - LLM worker with ModelManager, PromptManager, activity throttling
- **Enhanced Bakeoff**: `scripts/model_bakeoff_with_dedupe.py` - Per-hostname configs, interactive setup
- **Core Systems**: DedupeManager, ActivityMonitor, ConversationGrader, RAGPreprocessor
- **Health Check**: `scripts/health_check.py` - Pre-flight validation
- **Status Check**: `scripts/status.py` - Quick system overview

## Configuration (Per-Hostname)
**Orchestrator**: `config/orchestrator_config.json` (universal)
**Nodes**: `config/node_config.json` (per-hostname with interactive setup)
**Bakeoff**: `config/bakeoff_config.json` (per-hostname with interactive setup)
**Logging**: `config/logging.json`, `logs/` directory
**Auto-Setup**: Interactive prompts for missing configs with smart defaults

## Interactive Setup Features
- **Auto-Detection**: Checks for existing conversations, OpenAI keys in environment
- **Smart Defaults**: RAG enabled if data exists, hash-only deduplication, activity monitoring
- **Per-Hostname**: Each machine gets its own config section
- **Graceful Shutdown**: Ctrl+C properly shuts down with cleanup
- **Config Validation**: Startup checks database, LLM endpoints, dependencies

## Features
- **Interactive Setup**: Auto-creates configs with smart defaults, detects existing data
- **Activity Detection**: Auto-throttles during gaming, heavy usage with gradual scaling
- **Per-Hostname Configs**: Each machine maintains separate configuration
- **Graceful Operations**: Signal handling, startup validation, error recovery
- **Smart Defaults**: RAG (Y if data exists), deduplication (Y), grading (Y), activity monitoring (Y)
- **Auto-Discovery**: LM Studio models, OpenAI keys from environment
- **Master Preference**: EPM_DELL preferred with graceful takeover
- **Quality Pipeline**: Generation → Deduplication → Grading → Storage

## Current System State
- **Target**: 1000 conversations, 10 per job (100 jobs total)
- **Database**: PostgreSQL with pgvector, auto-retry with exponential backoff
- **Models**: Auto-detected from LM Studio, embedding models filtered
- **Deduplication**: Hash-only by default (faster), per-hostname runs
- **Activity Monitoring**: Gradual throttling, gaming detection, thermal protection
- **Configs**: Per-hostname with interactive setup, tracked in git
- **Logging**: Structured logging to console and files

## EPM_DELL Setup Checklist

### 1. Health Check
```bash
python scripts/health_check.py
```
**Expected**: Database OK, LM Studio OK, configs validated

### 2. System Status
```bash
python scripts/status.py
```
**Expected**: Shows current conversations, nodes, jobs

### 3. Trial Run (REQUIRED before production)
```bash
# Terminal 1
python src/master/orchestrator.py

# Terminal 2 (after orchestrator starts)
python src/nodes/generation_node.py 1
```
**Expected**: 1 conversation generated, graded, stored

### 4. Production Launch
```bash
# Terminal 1 (Master)
python src/master/orchestrator.py

# Terminal 2+ (Workers - multiple machines)
python src/nodes/generation_node.py
```
**Target**: 1000 conversations across all nodes

## Command Reference

### Health Check
```bash
python scripts/health_check.py
```

### System Status
```bash
python scripts/status.py
```

### Trial Run (1 conversation test)
```bash
# Terminal 1 (Master)
python src/master/orchestrator.py

# Terminal 2 (Generator - limit 1 job)
python src/nodes/generation_node.py 1
```

### Production Run (1000 conversations)
```bash
# Terminal 1 (Master)
python src/master/orchestrator.py

# Terminal 2+ (Generators - unlimited)
python src/nodes/generation_node.py
```

## Chat Command Mapping for EPM_DELL
- **"run health check"** → `python scripts/health_check.py`
- **"check status"** → `python scripts/status.py`
- **"run trial"** → Instructions for single conversation test
- **"start production"** → Instructions for 1000 conversation run
- **"confirm DELL ready"** → Full setup validation checklist
- **"emergency stop"** → Ctrl+C all terminals (graceful shutdown)

## Quick Commands for EPM_DELL Setup

### Pre-Flight Check
**"run health check"** → `python scripts/health_check.py`

### System Status
**"check status"** → `python scripts/status.py`

### Trial Run (Single Conversation)
**"run trial"** → Terminal 1: `python src/master/orchestrator.py`, Terminal 2: `python src/nodes/generation_node.py 1`

### Production Run (1000 Conversations)
**"start production"** → Terminal 1: `python src/master/orchestrator.py`, Terminal 2+: `python src/nodes/generation_node.py`

## Notes
- **First Run**: Will prompt for interactive config setup
- **Configs Tracked**: All configs now in git (per-hostname)
- **Auto-Recovery**: Database retries, model fallbacks, graceful errors
- **Multi-Node Ready**: Run generators on multiple machines simultaneously