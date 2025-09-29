# Dataset Analyzer - System Architecture

## Overview

The Dataset Analyzer is a modular tool designed to analyze conversation datasets and generate reusable templates for LLM-based conversation generation. The system follows a hierarchical classification approach: Domain → Category → Subcategory.

## Architecture Components

### Core Processing Pipeline

```
Input Files → File Scanner → Format Detector → Metadata Extractor → Classification Engine → Template Generator → Output
```

### Module Structure

#### 1. Core Modules (`src/core/`)
- **FileScanner**: Recursive directory traversal with incremental processing
- **FormatDetector**: Auto-detection and parsing of JSON, CSV, TXT, XML formats
- **MetadataExtractor**: Conversation analysis and quality metrics

#### 2. Classification Engine (`src/classification/`)
- **HierarchicalClassifier**: Domain/Category/Subcategory classification
- **PatternAnalyzer**: Structural pattern detection
- **VocabularyExtractor**: Domain-specific term extraction

#### 3. Template System (`src/templates/`)
- **TemplateGenerator**: Create reusable conversation templates
- **PromptBuilder**: LLM prompt construction
- **InheritanceManager**: Template hierarchy and inheritance
- **Exporters**: Multi-format output (YAML, JSON)

#### 4. LLM Integration (`src/llm/`)
- **ProviderFactory**: Unified interface for different LLM backends
- **OpenAIClient**: OpenAI API integration
- **LocalClient**: Local/Ollama endpoint support
- **ClassifierService**: LLM-powered classification

#### 5. User Interfaces (`src/interfaces/`)
- **CLI**: Command-line interface with Click framework
- **ProgressReporter**: Real-time progress tracking

#### 6. Utilities (`src/utils/`)
- **ConfigManager**: YAML configuration management
- **Logger**: Structured logging
- **FileUtils**: File I/O helpers

## Data Flow

### 1. File Discovery
```python
FileScanner.scan_directory() → Iterator[FileInfo]
```
- Recursive directory traversal
- File type filtering (.json, .csv, .txt, .xml)
- Incremental processing with hash-based caching

### 2. Format Detection & Parsing
```python
FormatDetector.detect_format() → FileFormat
FormatDetector.parse_file() → ConversationData
```
- Auto-detection by extension and content analysis
- Unified ConversationData structure
- Error handling for malformed files

### 3. Metadata Extraction
```python
MetadataExtractor.extract_conversation_metadata() → ConversationMetadata
```
- Turn count, speaker analysis
- Quality indicators (completeness, alternation)
- Conversation type classification

### 4. Classification (Future)
```python
HierarchicalClassifier.classify_conversation() → Classification
```
- Keyword-based initial classification
- LLM-powered refinement
- Confidence scoring

### 5. Template Generation (Future)
```python
TemplateGenerator.generate_templates() → TemplateSet
```
- Pattern-based template creation
- Inheritance hierarchy
- Few-shot example selection

## Configuration System

### Hierarchical Configuration
1. Command-line arguments (highest priority)
2. Custom config file (`--config path`)
3. Default config (`config/default_config.yaml`)
4. Built-in defaults (lowest priority)

### Configuration Structure
```yaml
processing:
  batch_size: 100
  parallel_workers: 4
  cache_enabled: true

llm:
  default_provider: "openai"
  classification_model: "gpt-4o-mini"

classification:
  confidence_threshold: 0.7
  use_llm_fallback: true

templates:
  max_examples_per_template: 5
  include_inheritance: true

output:
  template_format: "yaml"
  include_examples: true
```

## Extensibility Points

### 1. Format Parsers
Add new file format support by implementing `FormatParser` interface:
```python
class CustomParser(FormatParser):
    def can_parse(self, filepath: str) -> bool
    def parse(self, filepath: str) -> ConversationData
```

### 2. Classification Strategies
Implement different classification approaches:
```python
class CustomClassifier(ClassificationStrategy):
    def classify(self, conversation: ConversationData) -> Classification
```

### 3. LLM Providers
Add new LLM backends:
```python
class CustomProvider(LLMProvider):
    def classify_conversation(self, conversation: ConversationData) -> Classification
```

### 4. Export Formats
Support additional output formats:
```python
class CustomExporter(TemplateExporter):
    def export(self, templates: TemplateSet, output_path: str) -> None
```

## Error Handling Strategy

### Graceful Degradation
- Continue processing when individual files fail
- Log warnings for parsing errors
- Provide partial results when possible

### Recovery Mechanisms
- Resume capability for interrupted processing
- Incremental processing to skip unchanged files
- Comprehensive error logging

## Performance Considerations

### Scalability
- Streaming file processing to handle large datasets
- Parallel processing for CPU-intensive operations
- Memory-efficient data structures

### Caching
- File hash-based incremental processing
- Configuration caching
- Template result caching

## Security Considerations

### Data Privacy
- No data transmission to external services (unless explicitly configured)
- Local processing by default
- Configurable PII scrubbing (future)

### API Security
- Environment variable-based API key management
- Configurable timeout and retry policies
- Rate limiting for external API calls

## Future Enhancements

### Phase 1 (Current)
- ✅ File scanning and parsing
- ✅ Metadata extraction
- ✅ Basic CLI interface

### Phase 2 (Next)
- LLM-powered classification
- Template generation
- Pattern analysis

### Phase 3 (Future)
- Web interface
- Advanced analytics
- Distributed processing
- Real-time monitoring