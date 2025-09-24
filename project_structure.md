# Distributed Transcript Generation System - Project Structure

```
transcript-intelligence-platform/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── .gitignore
├── setup.py
│
├── config/
│   ├── __init__.py
│   ├── database_schema.sql
│   ├── default_config.yaml
│   └── node_profiles/
│       ├── master.yaml
│       ├── generation_node.yaml
│       ├── processing_node.yaml
│       └── pi_node.yaml
│
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config_manager.py
│   │   ├── database.py
│   │   ├── event_bus.py
│   │   └── base_node.py
│   │
│   ├── master/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── node_discovery.py
│   │   ├── work_distributor.py
│   │   ├── health_monitor.py
│   │   └── web_dashboard.py
│   │
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── generation_node.py
│   │   ├── processing_node.py
│   │   ├── hardware_detector.py
│   │   └── thermal_manager.py
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── stream_processor.py
│   │   ├── work_queue.py
│   │   ├── data_ingestion.py
│   │   └── output_formatter.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── llm_manager.py
│   │   ├── model_registry.py
│   │   ├── quality_scorer.py
│   │   └── gan_discriminator.py
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── scenario_engine.py
│   │   ├── persona_generator.py
│   │   ├── rag_manager.py
│   │   └── youtube_processor.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   ├── metrics.py
│   │   ├── security.py
│   │   └── file_utils.py
│   │
│   └── api/
│       ├── __init__.py
│       ├── rest_api.py
│       ├── websocket_handler.py
│       └── query_processor.py
│
├── web/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── assets/
│   ├── templates/
│   │   ├── dashboard.html
│   │   ├── nodes.html
│   │   ├── generation.html
│   │   └── analytics.html
│   └── components/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── models/
│   ├── outputs/
│   └── cache/
│
├── scripts/
│   ├── setup_node.py
│   ├── migrate_db.py
│   ├── health_check.py
│   └── benchmark.py
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   ├── integration/
│   └── performance/
│
└── docs/
    ├── architecture.md
    ├── api_reference.md
    ├── deployment.md
    └── configuration.md
```

## Key Design Principles

### 1. Configuration-Driven Architecture
- All settings stored in database with YAML fallbacks
- No hardcoded values in source code
- Environment-specific configurations
- Hot-reloadable settings

### 2. Modular Components
- Each module has single responsibility
- Clean interfaces between components
- Pluggable architecture for easy extension
- Dependency injection for testability

### 3. Database-First Configuration
- Central configuration store in PostgreSQL/SQLite
- Real-time configuration updates
- Configuration versioning and rollback
- Node-specific overrides

### 4. Scalable File Organization
- Logical separation by functionality
- Clear import paths
- Minimal circular dependencies
- Easy to navigate and maintain