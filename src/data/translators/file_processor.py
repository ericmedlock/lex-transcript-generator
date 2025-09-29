#!/usr/bin/env python3
"""
File Processor - Handle various file formats and extract conversation data
"""

import json
import csv
import os
from pathlib import Path
from typing import Dict, List, Any, Iterator, Optional
import logging

logger = logging.getLogger(__name__)

class FileProcessor:
    """Process various file formats to extract conversation data"""
    
    def __init__(self):
        self.supported_extensions = {'.json', '.jsonl', '.csv', '.txt'}
    
    def process_file(self, file_path: Path) -> Iterator[Dict[str, Any]]:
        """
        Process a file and yield conversation data
        
        Args:
            file_path: Path to the file to process
            
        Yields:
            Dict containing conversation data and metadata
        """
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
                    # Array of conversations
                    for i, item in enumerate(data):
                        yield {
                            'conversation_data': item,
                            'source_file': str(file_path),
                            'index': i,
                            'metadata': self._extract_file_metadata(file_path)
                        }
                elif isinstance(data, dict):
                    # Single conversation or structured data
                    if 'conversations' in data:
                        # Multiple conversations in a structure
                        for i, conv in enumerate(data['conversations']):
                            yield {
                                'conversation_data': conv,
                                'source_file': str(file_path),
                                'index': i,
                                'metadata': self._extract_file_metadata(file_path)
                            }
                    else:
                        # Single conversation
                        yield {
                            'conversation_data': data,
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
                        'conversation_data': data,
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
                # Look for conversation content in various column names
                content_columns = ['conversation', 'transcript', 'content', 'text', 'dialogue']
                conversation_data = None
                
                for col in content_columns:
                    if col in row and row[col]:
                        conversation_data = {'conversation': row[col]}
                        break
                
                if not conversation_data:
                    # Use all columns as conversation data
                    conversation_data = dict(row)
                
                yield {
                    'conversation_data': conversation_data,
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
            
            # Try to split into multiple conversations if separated by blank lines
            conversations = content.split('\n\n')
            
            for i, conv in enumerate(conversations):
                conv = conv.strip()
                if conv:
                    yield {
                        'conversation_data': {'conversation': conv},
                        'source_file': str(file_path),
                        'index': i,
                        'metadata': self._extract_file_metadata(file_path)
                    }
    
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
    
    def scan_directory(self, directory: Path, recursive: bool = True) -> Iterator[Path]:
        """
        Scan directory for supported files
        
        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            
        Yields:
            Path objects for supported files
        """
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
    
    def get_file_stats(self, directory: Path) -> Dict[str, Any]:
        """Get statistics about files in directory"""
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