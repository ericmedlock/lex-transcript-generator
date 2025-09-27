# LLM Transcript Data Generation Platform - Context Transfer

## System Overview
**Base Directory**: `C:\Users\ericm\PycharmProjects\LLM-Transcript-Data-Gen\`
**Database**: PostgreSQL (EPM_DELL:5432, calllab, postgres/pass)
**Output**: Amazon Connect Contact Lens v1.1.0 JSON format
**Architecture**: Distributed master/worker nodes with activity monitoring, deduplication, RAG integration

## Key Components
- **Enhanced Bakeoff**: `scripts/model_bakeoff_with_dedupe.py` - Multi-model benchmarking with activity monitoring, per-node deduplication
- **Master Node**: `src/master/orchestrator.py` - Job scheduler with EPM_DELL preference, heartbeat monitoring
- **Generation Node**: `src/nodes/generation_node.py` - LLM worker with RAG examples, duplicate detection
- **Deduplication**: `src/core/dedupe_manager.py` - Run-specific vector similarity checking
- **Activity Monitor**: `src/core/activity_monitor.py` - Gaming detection, resource throttling
- **RAG System**: `src/data/rag_preprocessor.py` - Vector embeddings via LM Studio (768d)

## Configuration
**Database Schema**: postgres_schema.sql, rag_schema.sql, dedupe_schema.sql
**Config**: config.json with deduplication, resource_management sections
**Dependencies**: psycopg2-binary, aiohttp, requests, psutil, openai

## Quick Commands (Chat Interface)

### System Check
**"confirm DELL is ready"** → Runs ready check command

### Debug Testing  
**"run 1 debug cycle on DELL"** → Sets trials=1, runs bakeoff

### Production Setup
**"update config for full run"** → Sets trials=50+ for production

### Full Run Command
**"give me command to do full run from terminal"** → Returns: `python scripts/model_bakeoff_with_dedupe.py`

## Command Reference

### Ready Check
```python
python -c "import sys,json; sys.path.append('src/core'); from dedupe_manager import DedupeManager; from activity_monitor import ActivityMonitor; c=json.load(open('config.json')); print('Machine:',c.get('machine_name')); print('Trials:',c.get('trials')); dm=DedupeManager(); am=ActivityMonitor(c); print('Dedup ready:',dm.embedding_model is not None); print('Activity ready:',am.activity_detection); print('Mode:',am.get_activity_mode()); print('Limits:',am.get_resource_limits()); print('System ready!')"
```

### Debug Setup (1 trial)
```python
python -c "import json; c=json.load(open('config.json')); c['trials']=1; c['machine_name']='EPM_DELL'; json.dump(c,open('config.json','w'),indent=2); print('Debug config set')"
```

### Production Setup (50 trials)
```python
python -c "import json; c=json.load(open('config.json')); c['trials']=50; c['machine_name']='EPM_DELL'; json.dump(c,open('config.json','w'),indent=2); print('Production config set')"
```

### Run Bakeoff
```bash
python scripts/model_bakeoff_with_dedupe.py
```

## Features
- **Activity Detection**: Auto-throttles during gaming (Steam, Epic, etc.)
- **Resource Limits**: Idle(80%/70%), Active(30%/20%), Gaming(20%/10%), Thermal(10%/5%)
- **Per-Node Deduplication**: Separate runs per machine for independent testing
- **RAG Integration**: Uses real conversation examples in prompts
- **Master Preference**: EPM_DELL becomes preferred master with graceful takeover
- **Output Organization**: Timestamped directories in output/tool_runs/
- **Quality Control**: OpenAI grading, vector similarity deduplication
- **Multi-Model Support**: Auto-detects LM Studio models, filters embedding models

## System State
- **Database**: PostgreSQL with pgvector extension for embeddings
- **Models**: Auto-detected from LM Studio /v1/models endpoint
- **Deduplication**: Run-specific tables with 0.85 similarity threshold
- **Activity Monitoring**: 5-second polling with process detection
- **Temperature Protection**: Auto-throttles at 80°C
- **Heartbeat**: 10-second intervals, 60-second failover timeout

## Chat Command Mapping
- **"confirm DELL is ready"** → Execute ready check command
- **"run 1 debug cycle on DELL"** → Set trials=1, run bakeoff
- **"update config for full run"** → Set trials=50+
- **"give me command to do full run from terminal"** → Return: `python scripts/model_bakeoff_with_dedupe.py`
- **"check system status"** → Show current config and component status
- **"view latest results"** → Run `python scripts/view_results.py`
- **"initialize schemas"** → Run `python scripts/init_dedupe_schema.py`