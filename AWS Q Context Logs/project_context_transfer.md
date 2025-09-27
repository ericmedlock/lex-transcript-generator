# LLM Transcript Data Generation Platform - Full Context Transfer

## Project Overview
**Base Directory**: `C:\Users\ericm\PycharmProjects\LLM-Transcript-Data-Gen\`
**Goal**: Distributed system for generating high-quality conversation transcripts using AI for training chatbots/conversational AI systems.

## Current System Architecture
- **Master Node**: Orchestrates job scheduling, node discovery, health monitoring
- **Generation Nodes**: Process LLM generation jobs, connect to LM Studio endpoints
- **Database**: PostgreSQL (host: EPM_DELL:5432, database: calllab, user: postgres, password: pass)
- **Output Format**: Amazon Connect Contact Lens v1.1.0 JSON format

## Key Files & Components

### Database Schema (`config/database/postgres_schema.sql`)
- **nodes**: Worker node registration and status
- **scenarios**: Conversation templates (healthcare, retail, telecom)
- **jobs**: Generation job queue with status tracking
- **conversations**: Generated transcripts with metadata (model_name, timing, evaluation_metrics)

### Core Scripts
- **Master**: `src/master/orchestrator.py` - Job scheduler and node coordinator
- **Generation Node**: `src/nodes/generation_node.py` - LLM worker that processes jobs
- **Model Bakeoff**: `scripts/model_bakeoff.py` - Multi-model benchmarking tool
- **Utilities**: `scripts/view_results.py`, `scripts/dump_results.py`, `scripts/check_jobs.py`

### Configuration (`config.json`)
```json
{
  "base_url": "http://localhost:1234/v1",
  "api_key": "lm-studio", 
  "machine_name": "MSI-Laptop-4050",
  "trials": 10,
  "temperature": 0.7,
  "max_tokens": 512,
  "timeout_s": 120,
  "unload_between_models": true,
  "prompt": "Generate realistic healthcare appointment conversation..."
}
```

## Current System State
- **Database**: Converted from SQLite to PostgreSQL
- **Model Selection**: Auto-detects available models from LM Studio `/v1/models` endpoint
- **Generation Node**: Uses first available model, tracks timing/metadata
- **Bakeoff Tool**: Tests all available models with system info detection (GPU, platform)

## Key Technical Details

### Database Connection (All Components)
```python
db_config = {
    'host': 'EPM_DELL',
    'port': 5432,
    'database': 'calllab', 
    'user': 'postgres',
    'password': 'pass'
}
```

### Generation Node Features
- Auto-registers with master node
- Processes jobs assigned by orchestrator
- Tracks model name, generation timing, quality scores
- Supports max_jobs parameter for testing (e.g., `python src/nodes/generation_node.py 3`)
- Converts LLM output to Contact Lens format with proper participant IDs

### Model Bakeoff Features
- Auto-detects system specs (GPU model, VRAM, platform)
- Tests all available models from LM Studio
- Generates CSV reports: `bakeoff_YYYYMMDD_HHMMSS.csv` (summary), `bakeoff_trials_YYYYMMDD_HHMMSS.csv` (per-trial)
- Optional model unloading between tests using `lms unload --all`
- Includes machine identification for multi-system benchmarking

### Conversation Format (Contact Lens v1.1.0)
```json
{
  "Version": "1.1.0",
  "Participants": [
    {"ParticipantId": "A1", "ParticipantRole": "AGENT"},
    {"ParticipantId": "C1", "ParticipantRole": "CUSTOMER"}
  ],
  "Transcript": [
    {"Id": "T000001", "Content": "...", "ParticipantId": "C1"}
  ]
}
```

## User Environment & Preferences
- **OS**: Windows with PowerShell
- **LLM Setup**: LM Studio on port 1234 (not Ollama)
- **Current Model**: microsoft/phi-4-mini-reasoning
- **Approach**: Step-by-step due to ADHD, prefers minimal code implementations
- **Hardware**: MSI laptop with RTX 4050, moving to bigger desktop

## Recent Changes Made
1. **Database Migration**: SQLite → PostgreSQL with proper schema
2. **Model Auto-Detection**: Removed hardcoded models, uses API discovery
3. **Enhanced Metadata**: Added model_name, timing, evaluation_metrics to conversations table
4. **System Detection**: GPU/platform info in bakeoff tool
5. **Job Counter Fix**: Only counts successful completions, not failures

## Current Commands
- **Start Master**: `python -m src.master.orchestrator`
- **Start Generation Node**: `python src/nodes/generation_node.py 10` (for 10 jobs)
- **Run Bakeoff**: `python scripts/model_bakeoff.py`
- **View Results**: `python scripts/view_results.py`
- **Check Jobs**: `python scripts/check_jobs.py`
- **Clear DB**: `TRUNCATE TABLE conversations, jobs RESTART IDENTITY CASCADE;`

## Dependencies Installed
- psycopg2-binary (PostgreSQL driver)
- aiohttp (async HTTP client)
- Standard libraries: asyncio, json, uuid, datetime

## Next Steps Context
User is moving to desktop machine and will need to:
1. Set up same PostgreSQL connection (EPM_DELL:5432)
2. Update config.json with new machine_name
3. Install dependencies and run bakeoff tool
4. System will auto-detect new GPU specs and include in results

## Important Notes
- **No data deletion**: System only INSERTs, never DELETEs conversations
- **Async architecture**: Uses asyncio for concurrent operations
- **Error handling**: Jobs can fail without breaking the system
- **Scalable design**: Supports multiple nodes, different hardware configs
- **Contact Lens compliance**: Output format matches Amazon Connect requirements