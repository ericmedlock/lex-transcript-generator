# API Reference

## Core Classes

### FileScanner

Recursively scans directories for conversation files with incremental processing support.

```python
from dataset_analyzer.src.core import FileScanner

scanner = FileScanner(cache_enabled=True)
for file_info in scanner.scan_directory("/path/to/datasets"):
    print(f"Found: {file_info.filepath}")
```

#### Methods

- `scan_directory(path: str) -> Iterator[FileInfo]`
  - Recursively scan directory for supported file types
  - Returns iterator of FileInfo objects
  - Supports incremental processing via file hashing

- `get_file_hash(filepath: str) -> str`
  - Generate MD5 hash for file content
  - Used for change detection in incremental processing

#### Supported Extensions
- `.json` - JSON conversation files
- `.csv` - Comma-separated values
- `.tsv` - Tab-separated values  
- `.txt` - Plain text conversations
- `.xml` - XML conversation files

### FormatDetector

Auto-detects file formats and parses conversation data into unified structure.

```python
from dataset_analyzer.src.core import FormatDetector

detector = FormatDetector()
format = detector.detect_format("conversation.json")
conversation = detector.parse_file("conversation.json", format)
```

#### Methods

- `detect_format(filepath: str) -> FileFormat`
  - Auto-detect file format by extension and content
  - Returns FileFormat enum value

- `parse_file(filepath: str, file_format: FileFormat = None) -> ConversationData`
  - Parse file into standardized ConversationData structure
  - Auto-detects format if not provided
  - Returns None if parsing fails

#### Supported Formats

**JSON Structure Examples:**
```json
// Array of turns
[
  {"speaker": "agent", "text": "Hello, how can I help?"},
  {"speaker": "customer", "text": "I need to schedule an appointment"}
]

// Object with turns array
{
  "speakers": ["agent", "customer"],
  "turns": [
    {"speaker": "agent", "text": "Hello, how can I help?"},
    {"speaker": "customer", "text": "I need to schedule an appointment"}
  ],
  "metadata": {"domain": "healthcare"}
}
```

**CSV Structure:**
```csv
speaker,text,timestamp
agent,"Hello, how can I help?",2024-01-01 10:00:00
customer,"I need to schedule an appointment",2024-01-01 10:00:05
```

### MetadataExtractor

Extracts comprehensive metadata from conversation data.

```python
from dataset_analyzer.src.core import MetadataExtractor

extractor = MetadataExtractor()
metadata = extractor.extract_conversation_metadata(conversation)
print(f"Turn count: {metadata.turn_count}")
print(f"Quality score: {metadata.quality_indicators['completeness']}")
```

#### Methods

- `extract_conversation_metadata(conversation: ConversationData) -> ConversationMetadata`
  - Extract comprehensive metadata from conversation
  - Returns structured metadata object

#### Metadata Fields

- `turn_count: int` - Number of conversation turns
- `speaker_count: int` - Number of unique speakers
- `avg_turn_length: float` - Average words per turn
- `total_length: int` - Total word count
- `speakers: List[str]` - List of speaker identifiers
- `conversation_type: str` - Detected conversation type
- `quality_indicators: Dict[str, Any]` - Quality metrics

#### Quality Indicators

- `completeness: float` - Ratio of non-empty turns (0-1)
- `alternation_score: float` - How well speakers alternate (0-1)
- `empty_turns: int` - Count of empty/missing turns
- `very_short_turns: int` - Count of turns with <2 words
- `has_timestamps: bool` - Whether turns include timestamps
- `has_confidence: bool` - Whether turns include confidence scores

## Data Models

### FileInfo

Information about discovered files.

```python
@dataclass
class FileInfo:
    filepath: str           # Full path to file
    size: int              # File size in bytes
    modified_time: float   # Last modification timestamp
    file_hash: str         # MD5 hash of file content
    extension: str         # File extension (lowercase)
```

### ConversationData

Unified conversation data structure.

```python
@dataclass
class ConversationData:
    speakers: List[str]              # List of speaker identifiers
    turns: List[Dict[str, Any]]      # List of conversation turns
    metadata: Dict[str, Any]         # Additional metadata
    source_file: str                 # Original file path
```

#### Turn Structure
Each turn in the `turns` list should contain:
- `speaker: str` - Speaker identifier
- `text: str` - Turn content/text
- Additional fields (timestamp, confidence, etc.) preserved as-is

### ConversationMetadata

Extracted conversation metadata.

```python
@dataclass
class ConversationMetadata:
    turn_count: int                    # Number of turns
    speaker_count: int                 # Number of speakers
    avg_turn_length: float            # Average words per turn
    total_length: int                 # Total word count
    speakers: List[str]               # Speaker identifiers
    conversation_type: str            # Conversation type
    quality_indicators: Dict[str, Any] # Quality metrics
    source_file: str                  # Source file path
```

### FileFormat

Enumeration of supported file formats.

```python
class FileFormat(Enum):
    JSON = "json"
    CSV = "csv"
    TXT = "txt"
    XML = "xml"
    TSV = "tsv"
    UNKNOWN = "unknown"
```

## Configuration Management

### ConfigManager

Manages hierarchical configuration loading and access.

```python
from dataset_analyzer.src.utils import ConfigManager

config = ConfigManager("custom_config.yaml")
batch_size = config.get("processing.batch_size", 100)
config.set("processing.parallel_workers", 8)
```

#### Methods

- `get(key: str, default: Any = None) -> Any`
  - Get configuration value using dot notation
  - Returns default if key not found

- `set(key: str, value: Any) -> None`
  - Set configuration value using dot notation
  - Creates nested structure as needed

#### Configuration Search Order
1. Explicitly provided config file
2. `config/default_config.yaml`
3. `../config/default_config.yaml`
4. Built-in defaults

## CLI Interface

### Main Commands

```bash
# Scan directory and analyze files
python -m dataset_analyzer scan --input /path/to/data --output ./results

# Generate templates (future)
python -m dataset_analyzer generate-templates --llm openai --export yaml

# Validate templates (future)
python -m dataset_analyzer validate --templates ./templates
```

### Global Options

- `--config, -c` - Custom configuration file path
- `--verbose, -v` - Enable verbose logging

### Scan Command Options

- `--input, -i` - Input directory to scan (required)
- `--output, -o` - Output directory (default: ./analysis_results)
- `--format, -f` - Output format: json, yaml, csv (default: yaml)

## Usage Examples

### Basic File Analysis

```python
from dataset_analyzer.src.core import FileScanner, FormatDetector, MetadataExtractor

# Initialize components
scanner = FileScanner()
detector = FormatDetector()
extractor = MetadataExtractor()

# Process files
for file_info in scanner.scan_directory("./data"):
    conversation = detector.parse_file(file_info.filepath)
    if conversation:
        metadata = extractor.extract_conversation_metadata(conversation)
        print(f"File: {file_info.filepath}")
        print(f"Turns: {metadata.turn_count}")
        print(f"Speakers: {metadata.speakers}")
        print(f"Quality: {metadata.quality_indicators['completeness']:.2f}")
```

### Custom Configuration

```python
from dataset_analyzer.src.utils import ConfigManager

# Load custom config
config = ConfigManager("my_config.yaml")

# Use in components
scanner = FileScanner(cache_enabled=config.get("processing.cache_enabled", True))
```

### CLI Usage

```bash
# Basic scan
python -m dataset_analyzer scan -i ./Training\ Datasets -o ./results

# Verbose output with custom config
python -m dataset_analyzer -c custom.yaml -v scan -i ./data -f json

# Export as CSV for analysis
python -m dataset_analyzer scan -i ./data -o ./analysis -f csv
```

## Error Handling

### Common Exceptions

- `FileNotFoundError` - Directory or file not found
- `PermissionError` - Insufficient file permissions
- `ValueError` - Invalid configuration or data format
- `json.JSONDecodeError` - Malformed JSON files
- `UnicodeDecodeError` - File encoding issues

### Error Recovery

The system is designed for graceful degradation:
- Individual file parsing errors don't stop processing
- Warnings logged for problematic files
- Partial results returned when possible
- Resume capability for interrupted processing

### Logging

```python
from dataset_analyzer.src.utils import setup_logger

logger = setup_logger(verbose=True)
logger.info("Processing started")
logger.warning("Skipping malformed file")
logger.error("Critical error occurred")
```