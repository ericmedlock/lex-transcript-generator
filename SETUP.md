# Node Setup Guide

## Prerequisites
- Python 3.9+ installed
- Git repository cloned
- Network access to EPM_DELL (database host)

## Quick Setup (10 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup LM Studio
1. **Download**: https://lmstudio.ai/
2. **Install** LM Studio
3. **Download models**: 
   - **Chat model**: Search for "gamma-1b" and download
   - **Embedding model**: Search for "nomic-embed" and download
4. **Load the chat model**: Click "gamma-1b", then "Load Model"
5. **Start server**: Go to "Local Server" tab, click "Start Server"
6. **Verify**: Visit http://localhost:1234/v1/models (should show your model)

### 3. Health Check
```bash
python scripts/health_check.py
```
**Expected**: Will prompt for interactive config setup if first run

### 3. Test Single Conversation
```bash
python src/nodes/generation_node.py 1
```
**Expected**: Generates 1 conversation, then exits

### 4. Start Production Node
```bash
python src/nodes/generation_node.py
```
**Expected**: Runs continuously, processing jobs from master

## Interactive Setup Prompts

**First run will ask for configuration. Recommended answers:**

```
Database host [EPM_DELL]: <ENTER>
Database port [5432]: <ENTER>
Database name [calllab]: <ENTER>
Database user [postgres]: <ENTER>
Database password [pass]: <ENTER>
LLM endpoint [http://127.0.0.1:1234/v1/chat/completions]: <ENTER>
LLM creativity (0.1=focused, 1.0=creative) [0.9]: <ENTER>
Max response length in tokens [2000]: <ENTER>
Use existing conversations as examples [Y/n]: <ENTER>
Check for duplicate conversations [Y/n]: <ENTER>
Fast duplicate check (hash-only, recommended) [Y/n]: <ENTER>
Grade conversations with OpenAI [Y/n]: n
Enable activity monitoring [Y/n]: <ENTER>
```

## Requirements

### LM Studio (Required)
- Install LM Studio
- Load any chat model (not embedding model)
- Start server on default port 1234
- **Test**: Visit http://localhost:1234/v1/models

### Network Access (Required)
- Must reach EPM_DELL:5432 (PostgreSQL database)
- **Test**: `telnet EPM_DELL 5432` or `ping EPM_DELL`

### OpenAI API (Optional)
- Set `OPENAI_API_KEY` environment variable for grading
- Or answer 'n' to grading prompt

## Troubleshooting

### "Database connection failed"
- Check network connection to EPM_DELL
- Verify EPM_DELL is running PostgreSQL on port 5432

### "No chat models available"
- Start LM Studio server
- Load a chat model (not embedding model)
- Check http://localhost:1234/v1/models shows models

### "Config prompts not appearing"
- Delete `config/node_config.json` to force re-setup
- Or edit the file manually

## File Structure After Setup
```
config/
├── node_config.json     # Your hostname's config
└── logging.json         # Logging configuration

logs/
└── system.log          # Runtime logs
```

## Commands Reference

### Health Check
```bash
python scripts/health_check.py
```

### System Status
```bash
python scripts/status.py
```

### Single Job Test
```bash
python src/nodes/generation_node.py 1
```

### Production Mode
```bash
python src/nodes/generation_node.py
```

### Stop Gracefully
```
Ctrl+C (will finish current job then exit)
```

## Master Node (EPM_DELL Only)

If setting up the master node on EPM_DELL:

```bash
# Terminal 1 - Master
python src/master/orchestrator.py

# Terminal 2 - Local Generator
python src/nodes/generation_node.py
```

## Success Indicators

✅ **Health check passes**
✅ **Single job test completes**
✅ **Node shows up in status check**
✅ **Conversations appear in database**

## Need Help?

1. Run health check first: `python scripts/health_check.py`
2. Check system status: `python scripts/status.py`
3. Look at logs: `logs/system.log`
4. Verify LM Studio: http://localhost:1234/v1/models