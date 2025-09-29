# Dataset Analyzer & Template Generator

A modular tool for analyzing conversation datasets and generating reusable templates for LLM-based conversation generation.

## Features

- **Hierarchical Classification**: Domain → Category → Subcategory taxonomy
- **Multi-Format Support**: JSON, CSV, TXT, XML auto-detection
- **Template Generation**: Reusable conversation templates with inheritance
- **LLM Integration**: OpenAI API, local endpoints, Ollama support
- **Pattern Analysis**: Structural and content pattern extraction

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Analyze datasets
python -m dataset_analyzer scan --input ../Training\ Datasets --output ./analysis_results

# Generate templates
python -m dataset_analyzer generate-templates --llm openai --export yaml
```

## Configuration

Edit `config/default_config.yaml` to customize:
- LLM providers and models
- Classification taxonomy
- Processing parameters
- Output formats

## Documentation

See `docs/` directory for detailed system documentation.