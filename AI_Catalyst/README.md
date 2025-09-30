# AI_Catalyst Framework

A collection of proven, reusable AI components extracted from production systems for building robust LLM applications.

## Features

- **Three-Tier LLM System** - Local/Network/OpenAI provider support with automatic failover
- **PII Detection & Scrubbing** - LLM-based PII detection with regex fallback
- **Multi-Format File Processing** - JSON, JSONL, CSV, TXT file handling
- **Database Patterns** - Async PostgreSQL connection pooling and utilities
- **Configuration Management** - Database-first config with YAML fallbacks
- **System Monitoring** - Hardware detection and performance tuning

## Installation

```bash
pip install ai-catalyst
```

## Quick Start

```python
from ai_catalyst import LLMProvider, FileProcessor, PIIProcessor

# Three-tier LLM system
llm = LLMProvider()
response = await llm.generate("Analyze this conversation...")

# File processing
processor = FileProcessor()
data = await processor.process_file("conversations.json")

# PII scrubbing
pii = PIIProcessor()
clean_text = await pii.scrub_text("John Smith called 555-1234")
```

## Components

### LLM Providers
- Local LLM endpoints (LM Studio, Ollama)
- Network LLM endpoints
- OpenAI API with automatic failover

### Data Processing
- Multi-format file processors
- PII detection and scrubbing
- Metadata extraction

### Infrastructure
- Async database patterns
- Configuration management
- System monitoring

## Development

```bash
git clone https://github.com/ericmedlock/AI_Catalyst
cd AI_Catalyst
pip install -e .[dev]
pytest
```

## License

MIT License - see LICENSE file for details.