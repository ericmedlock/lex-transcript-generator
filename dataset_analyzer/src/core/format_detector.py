"""File format detection and parsing module"""

import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class FileFormat(Enum):
    JSON = "json"
    CSV = "csv"
    TXT = "txt"
    XML = "xml"
    TSV = "tsv"
    UNKNOWN = "unknown"

@dataclass
class ConversationData:
    speakers: List[str]
    turns: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    source_file: str

class FormatDetector:
    """Auto-detect file formats and parse conversation data"""
    
    def detect_format(self, filepath: str) -> FileFormat:
        """Detect file format based on extension and content"""
        path = Path(filepath)
        extension = path.suffix.lower()
        
        # Primary detection by extension
        format_map = {
            '.json': FileFormat.JSON,
            '.csv': FileFormat.CSV,
            '.tsv': FileFormat.TSV,
            '.txt': FileFormat.TXT,
            '.xml': FileFormat.XML
        }
        
        detected_format = format_map.get(extension, FileFormat.UNKNOWN)
        
        # Validate by content inspection
        if detected_format != FileFormat.UNKNOWN:
            if self._validate_format_by_content(filepath, detected_format):
                return detected_format
        
        # Fallback content-based detection
        return self._detect_by_content(filepath)
    
    def parse_file(self, filepath: str, file_format: FileFormat = None) -> Optional[ConversationData]:
        """Parse file into ConversationData"""
        if file_format is None:
            file_format = self.detect_format(filepath)
        
        try:
            if file_format == FileFormat.JSON:
                return self._parse_json(filepath)
            elif file_format == FileFormat.CSV:
                return self._parse_csv(filepath)
            elif file_format == FileFormat.TSV:
                return self._parse_csv(filepath, delimiter='\t')
            elif file_format == FileFormat.TXT:
                return self._parse_txt(filepath)
            elif file_format == FileFormat.XML:
                return self._parse_xml(filepath)
            else:
                print(f"Unsupported format: {file_format}")
                return None
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return None
    
    def _validate_format_by_content(self, filepath: str, expected_format: FileFormat) -> bool:
        """Validate format by inspecting file content"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline().strip()
            
            if expected_format == FileFormat.JSON:
                return first_line.startswith('{') or first_line.startswith('[')
            elif expected_format == FileFormat.XML:
                return first_line.startswith('<?xml') or first_line.startswith('<')
            elif expected_format in [FileFormat.CSV, FileFormat.TSV]:
                delimiter = '\t' if expected_format == FileFormat.TSV else ','
                return delimiter in first_line
            
            return True
        except Exception:
            return False
    
    def _detect_by_content(self, filepath: str) -> FileFormat:
        """Detect format by analyzing file content"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1024)  # Read first 1KB
            
            content = content.strip()
            if content.startswith('{') or content.startswith('['):
                return FileFormat.JSON
            elif content.startswith('<?xml') or content.startswith('<'):
                return FileFormat.XML
            elif '\t' in content:
                return FileFormat.TSV
            elif ',' in content:
                return FileFormat.CSV
            else:
                return FileFormat.TXT
        except Exception:
            return FileFormat.UNKNOWN
    
    def _parse_json(self, filepath: str) -> ConversationData:
        """Parse JSON conversation file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            # Array of turns
            turns = data
            speakers = list(set(turn.get('speaker', 'unknown') for turn in turns if isinstance(turn, dict)))
            metadata = {}
        elif isinstance(data, dict):
            if 'turns' in data:
                turns = data['turns']
                speakers = data.get('speakers', [])
                metadata = {k: v for k, v in data.items() if k not in ['turns', 'speakers']}
            else:
                # Single conversation object
                turns = [data]
                speakers = [data.get('speaker', 'unknown')]
                metadata = {}
        else:
            raise ValueError("Unsupported JSON structure")
        
        return ConversationData(
            speakers=speakers,
            turns=turns,
            metadata=metadata,
            source_file=filepath
        )
    
    def _parse_csv(self, filepath: str, delimiter: str = ',') -> ConversationData:
        """Parse CSV conversation file"""
        turns = []
        speakers = set()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                # Common CSV column mappings
                speaker = row.get('speaker') or row.get('Speaker') or row.get('role') or 'unknown'
                text = row.get('text') or row.get('Text') or row.get('message') or row.get('content', '')
                
                speakers.add(speaker)
                turns.append({
                    'speaker': speaker,
                    'text': text,
                    **{k: v for k, v in row.items() if k not in ['speaker', 'text', 'Speaker', 'Text']}
                })
        
        return ConversationData(
            speakers=list(speakers),
            turns=turns,
            metadata={'format': 'csv'},
            source_file=filepath
        )
    
    def _parse_txt(self, filepath: str) -> ConversationData:
        """Parse plain text conversation file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple heuristic: lines starting with "Speaker:" or similar
        lines = content.split('\n')
        turns = []
        speakers = set()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for speaker patterns
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    speaker = parts[0].strip()
                    text = parts[1].strip()
                    speakers.add(speaker)
                    turns.append({'speaker': speaker, 'text': text})
                    continue
            
            # Fallback: treat as single speaker
            turns.append({'speaker': 'unknown', 'text': line})
        
        return ConversationData(
            speakers=list(speakers) if speakers else ['unknown'],
            turns=turns,
            metadata={'format': 'txt'},
            source_file=filepath
        )
    
    def _parse_xml(self, filepath: str) -> ConversationData:
        """Parse XML conversation file"""
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        turns = []
        speakers = set()
        
        # Common XML structures
        for turn_elem in root.findall('.//turn') or root.findall('.//message') or root.findall('.//utterance'):
            speaker = turn_elem.get('speaker') or turn_elem.find('speaker')
            text = turn_elem.text or turn_elem.find('text')
            
            if speaker is not None:
                speaker = speaker.text if hasattr(speaker, 'text') else str(speaker)
            else:
                speaker = 'unknown'
            
            if text is not None:
                text = text.text if hasattr(text, 'text') else str(text)
            else:
                text = ''
            
            speakers.add(speaker)
            turns.append({'speaker': speaker, 'text': text})
        
        return ConversationData(
            speakers=list(speakers),
            turns=turns,
            metadata={'format': 'xml'},
            source_file=filepath
        )