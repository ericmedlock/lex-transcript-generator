"""
File Processor - Multi-format file processing for AI applications

Supports JSON, JSONL, CSV, TXT formats with metadata extraction.
"""

import json
import csv
import os
from pathlib import Path
from typing import Dict, List, Any, Iterator, Optional, Union
import logging

logger = logging.getLogger(__name__)


class FileProcessor:
    """Process various file formats to extract structured data"""
    
    def __init__(self, supported_extensions: Optional[set] = None):
        """
        Initialize file processor
        
        Args:
            supported_extensions: Set of supported file extensions (default: .json, .jsonl, .csv, .txt)
        """
        self.supported_extensions = supported_extensions or {'.json', '.jsonl', '.csv', '.txt'}
    
    def process_file(self, file_path: Union[str, Path]) -> Iterator[Dict[str, Any]]:
        """
        Process a file and yield structured data
        
        Args:
            file_path: Path to the file to process
            
        Yields:
            Dict containing data and metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return
        
        extension = file_path.suffix.lower()
        
        try:
            if extension == '.json':
                yield from self._process_json(file_path)
            elif extension == '.jsonl':
                yield from self._process_jsonl(file_path)
            elif extension == '.csv':
                yield from self._process_csv(file_path)
            elif extension == '.txt':
                yield from self._process_txt(file_path)
            else:
                logger.warning(f"Unsupported file type: {extension}")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    def _process_json(self, file_path: Path) -> Iterator[Dict[str, Any]]:
        """Process JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                
                # Handle different JSON structures
                if isinstance(data, list):
                    # Array of items
                    for i, item in enumerate(data):
                        yield {
                            'data': item,
                            'source_file': str(file_path),
                            'index': i,
                            'metadata': self._extract_file_metadata(file_path)
                        }
                elif isinstance(data, dict):
                    # Single item or structured data
                    if self._is_multi_item_structure(data):
                        # Multiple items in a structure
                        items = self._extract_items_from_structure(data)
                        for i, item in enumerate(items):
                            yield {
                                'data': item,
                                'source_file': str(file_path),
                                'index': i,
                                'metadata': self._extract_file_metadata(file_path)
                            }
                    else:
                        # Single item
                        yield {
                            'data': data,
                            'source_file': str(file_path),
                            'index': 0,
                            'metadata': self._extract_file_metadata(file_path)
                        }
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {file_path}: {e}")
    
    def _process_jsonl(self, file_path: Path) -> Iterator[Dict[str, Any]]:
        """Process JSONL (JSON Lines) file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    yield {
                        'data': data,
                        'source_file': str(file_path),
                        'index': i,
                        'metadata': self._extract_file_metadata(file_path)
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON line {i+1} in {file_path}: {e}")
    
    def _process_csv(self, file_path: Path) -> Iterator[Dict[str, Any]]:
        """Process CSV file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)
            
            delimiter = ','
            if '\t' in sample and sample.count('\t') > sample.count(','):
                delimiter = '\t'
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for i, row in enumerate(reader):
                yield {
                    'data': dict(row),
                    'source_file': str(file_path),
                    'index': i,
                    'metadata': self._extract_file_metadata(file_path)
                }
    
    def _process_txt(self, file_path: Path) -> Iterator[Dict[str, Any]]:
        """Process text file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
            if not content:
                return
            
            # Try to split into multiple sections if separated by blank lines
            sections = content.split('\n\n')
            
            for i, section in enumerate(sections):
                section = section.strip()
                if section:
                    yield {
                        'data': {'content': section},
                        'source_file': str(file_path),
                        'index': i,
                        'metadata': self._extract_file_metadata(file_path)
                    }
    
    def _is_multi_item_structure(self, data: dict) -> bool:
        """Check if dict contains multiple items in known structures"""
        # Common patterns for multi-item structures
        multi_item_keys = ['conversations', 'items', 'data', 'records', 'entries']
        return any(key in data and isinstance(data[key], list) for key in multi_item_keys)
    
    def _extract_items_from_structure(self, data: dict) -> List[Any]:
        """Extract items from structured data"""
        multi_item_keys = ['conversations', 'items', 'data', 'records', 'entries']
        for key in multi_item_keys:
            if key in data and isinstance(data[key], list):
                return data[key]
        return [data]  # Fallback to single item
    
    def _extract_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from file path and stats"""
        stat = file_path.stat()
        
        return {
            'filename': file_path.name,
            'file_size': stat.st_size,
            'created_time': stat.st_ctime,
            'modified_time': stat.st_mtime,
            'directory': str(file_path.parent),
            'extension': file_path.suffix
        }
    
    def scan_directory(self, directory: Union[str, Path], recursive: bool = True) -> Iterator[Path]:
        """
        Scan directory for supported files
        
        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            
        Yields:
            Path objects for supported files
        """
        directory = Path(directory)
        
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return
        
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                yield file_path
    
    def get_directory_stats(self, directory: Union[str, Path]) -> Dict[str, Any]:
        """Get statistics about files in directory"""
        directory = Path(directory)
        
        stats = {
            'total_files': 0,
            'by_extension': {},
            'total_size': 0,
            'directories': set()
        }
        
        for file_path in self.scan_directory(directory):
            stats['total_files'] += 1
            stats['total_size'] += file_path.stat().st_size
            stats['directories'].add(str(file_path.parent))
            
            ext = file_path.suffix.lower()
            stats['by_extension'][ext] = stats['by_extension'].get(ext, 0) + 1
        
        stats['directories'] = len(stats['directories'])
        return stats
    
    def process_directory(self, directory: Union[str, Path], recursive: bool = True) -> Iterator[Dict[str, Any]]:
        """Process all supported files in a directory"""
        for file_path in self.scan_directory(directory, recursive):
            yield from self.process_file(file_path)