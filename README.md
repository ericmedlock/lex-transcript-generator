# Distributed Transcript Intelligence Platform

A sophisticated, distributed system for generating high-quality conversation transcripts using AI, designed for training chatbots and conversational AI systems.

## 🚀 Features

### Core Capabilities
- **Distributed Processing**: Master/worker architecture across multiple machines
- **Intelligent Resource Management**: Automatic thermal throttling and activity detection
- **Multi-Domain Support**: Healthcare, retail, telecommunications, and custom domains
- **Quality Assurance**: GAN-style feedback loops for continuous improvement
- **RAG Integration**: Leverage massive public datasets for training
- **YouTube Processing**: Extract and process audio from YouTube videos
- **Multiple Output Formats**: Lex Contact Lens, Dialogflow, Rasa, and custom formats

### Advanced Features
- **Hardware Auto-Discovery**: Automatic detection of GPUs, CPUs, and capabilities
- **Thermal Management**: Dynamic throttling based on temperature monitoring
- **Activity Detection**: Gaming mode, work hours, and idle usage optimization
- **Streaming Pipeline**: Real-time data processing with reactive work distribution
- **Web Dashboard**: Real-time monitoring and control interface
- **Natural Language Queries**: "Generate 500 healthcare transcripts with frustrated callers"
- **Raspberry Pi Support**: Native llama.cpp integration for ARM devices
- **Batch Processing**: Optimized multi-conversation generation per LLM call
- **Memory Optimization**: In-memory caching and larger context windows
- **Smart Deduplication**: Hash-based and semantic similarity detection

## 🏗️ Architecture

```
Master Node (Orchestration)
├── Node Discovery & Health Monitoring
├── Work Distribution Engine
├── Configuration Management
├── Web Dashboard
└── Central Database

Generation Nodes (Content Creation)
├── LLM Inference Engines
├── Conversation Generation
├── Thermal Monitoring
└── Activity Detection

Processing Nodes (Quality Control)
├── Quality Scoring
├── Deduplication
├── Data Validation
└── GAN Discriminator
```

## 📁 Project Structure

```
transcript-intelligence-platform/
├── config/                 # Configuration files and node profiles
├── src/
│   ├── core/               # Core system components
│   ├── master/             # Master node orchestration
│   ├── nodes/              # Worker node implementations
│   ├── pipeline/           # Data processing pipeline
│   ├── models/             # AI model management
│   ├── data/               # Data processing and RAG
│   └── api/                # REST and WebSocket APIs
├── web/                    # Web dashboard interface
├── data/                   # Data storage directories
└── scripts/                # Setup and maintenance scripts
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL (or SQLite for development)
- Node.js (for web dashboard)
- Docker (optional)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd transcript-intelligence-platform
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Setup environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Initialize database**
```bash
python scripts/migrate_db.py
```

5. **Start master node**
```bash
python -m src.master.orchestrator
```

6. **Start worker nodes** (on other machines)
```bash
python -m src.nodes.generation_node
# or
python -m src.nodes.processing_node
```

## 🔧 Configuration

### Database-First Configuration
All system settings are stored in the database with YAML fallbacks:

```yaml
# config/default_config.yaml
generation:
  default_batch_size: 10
  conversation_length:
    simple: [20, 40]
    complex: [80, 150]

thermal:
  cpu_temp_limit: 80
  gpu_temp_limit: 85
```

### Node Profiles
Different node types have specialized configurations:
- `orchestrator_config.json` - Master node settings and job parameters
- `node_config.json` - Per-hostname generation node settings
- Raspberry Pi nodes use llama.cpp with local model inference
- Desktop nodes use HTTP API endpoints (LM Studio, etc.)
- Automatic Pi detection and optimization

## 🎯 Usage Examples

### Generate Healthcare Transcripts
```python
from src.api.query_processor import QueryProcessor

processor = QueryProcessor()
result = await processor.process_query(
    "Generate 100 healthcare appointment transcripts with insurance issues"
)
```

### Process YouTube Content
```python
from src.data.youtube_processor import YouTubeProcessor

processor = YouTubeProcessor()
transcripts = await processor.process_url(
    "https://youtube.com/watch?v=example"
)
```

### Web Dashboard
Access the web dashboard at `http://localhost:8080` for:
- Real-time node monitoring
- Generation job management
- Quality metrics and analytics
- Configuration management

## 🔍 Monitoring

### Metrics Available
- Generation rate (conversations/hour)
- Quality scores and trends
- Node performance and health
- Resource utilization
- Error rates and failures

### Health Checks
```bash
python scripts/health_check.py
```

## 🛠️ Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
black src/
flake8 src/
mypy src/
```

### Adding New Domains
1. Create scenario templates in database
2. Add domain-specific validation rules
3. Configure specialized models
4. Update web interface

## 📊 Performance

### Typical Performance
- **Generation Rate**: 1,000+ conversations/hour per GPU node, 100+ per Pi
- **Quality Score**: 95%+ pass validation
- **Duplicate Rate**: <5% semantic similarity
- **System Uptime**: 99%+ with automatic recovery
- **Batch Efficiency**: 30 conversations per LLM call
- **Memory Usage**: 16GB+ recommended for optimal Pi performance

### Scaling
- Supports 50+ nodes in cluster
- Horizontal scaling with load balancing
- Automatic failover and recovery
- Hot-swappable node addition/removal

## 🔒 Security

- JWT-based authentication
- Encrypted inter-node communication
- PHI scrubbing for medical data
- Configurable access controls
- Audit logging

## 📝 License

[Your License Here]

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## 📞 Support

- Documentation: `docs/`
- Issues: GitHub Issues
- Discussions: GitHub Discussions