# Usage Guide

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
cd dataset_analyzer
pip install -r requirements.txt
```

### Optional: OpenAI API Setup
If you plan to use OpenAI for classification:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Quick Start

### 1. Basic File Analysis

Analyze all conversation files in a directory:

```bash
python -m dataset_analyzer scan --input "../Training Datasets" --output ./analysis_results
```

This will:
- Recursively scan the input directory
- Parse all supported file formats (JSON, CSV, TXT, XML)
- Extract metadata from each conversation
- Save results to `./analysis_results/scan_results.yaml`

### 2. View Results

The output file contains detailed analysis:

```yaml
scan_results:
  - file_info:
      filepath: "/path/to/conversation1.json"
      size: 1024
      extension: ".json"
    metadata:
      turn_count: 15
      speaker_count: 2
      avg_turn_length: 12.5
      total_length: 187
      speakers: ["agent", "customer"]
      conversation_type: "dialogue"
      quality_indicators:
        completeness: 1.0
        alternation_score: 0.93
        empty_turns: 0
        very_short_turns: 1
        has_timestamps: false
        has_confidence: false
total_files: 42
```

## Command Reference

### Global Options

```bash
python -m dataset_analyzer [OPTIONS] COMMAND [ARGS]
```

**Options:**
- `--config, -c PATH` - Custom configuration file
- `--verbose, -v` - Enable verbose logging
- `--help` - Show help message

### Scan Command

Analyze conversation files in a directory.

```bash
python -m dataset_analyzer scan [OPTIONS]
```

**Options:**
- `--input, -i PATH` - Input directory to scan (required)
- `--output, -o PATH` - Output directory (default: ./analysis_results)
- `--format, -f FORMAT` - Output format: yaml, json, csv (default: yaml)

**Examples:**

```bash
# Basic scan with YAML output
python -m dataset_analyzer scan -i ./data -o ./results

# JSON output for programmatic processing
python -m dataset_analyzer scan -i ./data -o ./results -f json

# CSV output for spreadsheet analysis
python -m dataset_analyzer scan -i ./data -o ./results -f csv

# Verbose logging
python -m dataset_analyzer -v scan -i ./data
```

## Configuration

### Configuration Files

The system uses YAML configuration files with hierarchical loading:

1. Custom config file (via `--config`)
2. `config/default_config.yaml`
3. Built-in defaults

### Default Configuration

```yaml
processing:
  batch_size: 100              # Files to process in each batch
  parallel_workers: 4          # Number of parallel workers
  cache_enabled: true          # Enable incremental processing
  incremental_processing: true # Skip unchanged files

llm:
  default_provider: "openai"   # LLM provider (openai, local, ollama)
  classification_model: "gpt-4o-mini"  # Model for classification
  max_retries: 3              # API retry attempts
  timeout: 30                 # Request timeout in seconds

classification:
  confidence_threshold: 0.7    # Minimum confidence for classification
  use_llm_fallback: true      # Use LLM when keyword classification fails
  keyword_weight: 0.3         # Weight for keyword-based classification
  llm_weight: 0.7            # Weight for LLM-based classification

templates:
  max_examples_per_template: 5    # Examples to include in templates
  include_inheritance: true       # Enable template inheritance
  min_conversations_per_template: 3  # Minimum conversations to create template

output:
  template_format: "yaml"      # Template output format
  include_examples: true       # Include example conversations
  export_confidence_scores: true  # Include confidence in output
  create_reports: true        # Generate analysis reports
```

### Custom Configuration

Create a custom configuration file:

```yaml
# my_config.yaml
processing:
  parallel_workers: 8
  batch_size: 200

llm:
  default_provider: "local"
  classification_model: "llama3"

output:
  template_format: "json"
```

Use with:
```bash
python -m dataset_analyzer -c my_config.yaml scan -i ./data
```

## Supported File Formats

### JSON Conversations

**Array Format:**
```json
[
  {
    "speaker": "agent",
    "text": "Hello, how can I help you today?",
    "timestamp": "2024-01-01T10:00:00Z"
  },
  {
    "speaker": "customer", 
    "text": "I need to schedule an appointment",
    "timestamp": "2024-01-01T10:00:05Z"
  }
]
```

**Object Format:**
```json
{
  "conversation_id": "conv_123",
  "speakers": ["agent", "customer"],
  "domain": "healthcare",
  "turns": [
    {
      "speaker": "agent",
      "text": "Hello, how can I help you today?"
    },
    {
      "speaker": "customer",
      "text": "I need to schedule an appointment"
    }
  ]
}
```

### CSV Conversations

```csv
speaker,text,timestamp,confidence
agent,"Hello, how can I help you today?",2024-01-01 10:00:00,0.95
customer,"I need to schedule an appointment",2024-01-01 10:00:05,0.92
agent,"I'd be happy to help you schedule an appointment",2024-01-01 10:00:10,0.98
```

**Required Columns:**
- `speaker` or `Speaker` - Speaker identifier
- `text` or `Text` or `message` or `content` - Turn content

**Optional Columns:**
- `timestamp` - Turn timestamp
- `confidence` - Confidence score
- Any other columns are preserved as metadata

### Plain Text Conversations

```
Agent: Hello, how can I help you today?
Customer: I need to schedule an appointment
Agent: I'd be happy to help you schedule an appointment
Customer: Great, I need to see Dr. Smith next week
```

**Format Requirements:**
- Each line represents one turn
- Format: `Speaker: Text`
- Empty lines are ignored

### XML Conversations

```xml
<?xml version="1.0" encoding="UTF-8"?>
<conversation>
  <turn speaker="agent">
    <text>Hello, how can I help you today?</text>
    <timestamp>2024-01-01T10:00:00Z</timestamp>
  </turn>
  <turn speaker="customer">
    <text>I need to schedule an appointment</text>
    <timestamp>2024-01-01T10:00:05Z</timestamp>
  </turn>
</conversation>
```

**Supported Elements:**
- `<turn>`, `<message>`, or `<utterance>` for individual turns
- `speaker` attribute or `<speaker>` element
- `<text>` element or direct text content

## Understanding Output

### Metadata Fields

**Basic Metrics:**
- `turn_count` - Total number of conversation turns
- `speaker_count` - Number of unique speakers
- `avg_turn_length` - Average words per turn
- `total_length` - Total word count across all turns
- `speakers` - List of speaker identifiers

**Conversation Types:**
- `monologue` - Single speaker
- `dialogue` - Two speakers
- `multi_party` - Three or more speakers

**Quality Indicators:**
- `completeness` (0-1) - Ratio of non-empty turns
- `alternation_score` (0-1) - How well speakers alternate
- `empty_turns` - Count of empty or missing turns
- `very_short_turns` - Count of turns with fewer than 2 words
- `has_timestamps` - Whether turns include timestamp information
- `has_confidence` - Whether turns include confidence scores

### Quality Assessment

**High Quality Conversations:**
- `completeness` > 0.9 (few empty turns)
- `alternation_score` > 0.7 (good speaker alternation)
- `avg_turn_length` > 5 (substantial content per turn)
- `very_short_turns` < 10% of total turns

**Potential Issues:**
- Low completeness indicates missing or empty content
- Low alternation score suggests poor conversation flow
- High number of very short turns may indicate parsing issues

## Troubleshooting

### Common Issues

**"No files found"**
- Check input directory path
- Ensure files have supported extensions (.json, .csv, .txt, .xml)
- Verify file permissions

**"Failed to parse file"**
- Check file format and encoding
- Look for malformed JSON or CSV
- Review verbose logs for specific errors

**"Permission denied"**
- Ensure read permissions on input directory
- Ensure write permissions on output directory
- Check file ownership and access rights

### Debugging

Enable verbose logging for detailed information:

```bash
python -m dataset_analyzer -v scan -i ./data
```

This will show:
- Files being processed
- Parsing errors and warnings
- Performance metrics
- Configuration details

### Performance Optimization

**For Large Datasets:**
- Increase `parallel_workers` in configuration
- Enable `cache_enabled` for incremental processing
- Use `batch_size` to control memory usage

**For Slow Processing:**
- Check disk I/O performance
- Reduce `parallel_workers` if CPU-bound
- Monitor memory usage

### File Format Issues

**JSON Files:**
- Ensure valid JSON syntax
- Check for proper UTF-8 encoding
- Verify expected structure (array or object with turns)

**CSV Files:**
- Ensure proper delimiter (comma for CSV, tab for TSV)
- Check for required columns (speaker, text)
- Verify encoding (UTF-8 recommended)

**Text Files:**
- Ensure consistent speaker format (`Speaker: Text`)
- Check for proper line endings
- Verify encoding

## Next Steps

### Future Features (Not Yet Implemented)

**Template Generation:**
```bash
python -m dataset_analyzer generate-templates --llm openai --export yaml
```

**Template Validation:**
```bash
python -m dataset_analyzer validate --templates ./templates --sample-size 10
```

**Classification:**
- Automatic domain/category/subcategory classification
- LLM-powered conversation analysis
- Custom taxonomy support

### Integration

The tool is designed to integrate with:
- LLM-based conversation generation systems
- Chatbot training pipelines
- Data quality assessment workflows
- Template-driven content creation

### Extending the Tool

See the API Reference for information on:
- Adding new file format parsers
- Implementing custom classification strategies
- Creating new export formats
- Extending the CLI interface