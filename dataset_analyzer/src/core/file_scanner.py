"""File scanning and discovery module"""

import os
import hashlib
from pathlib import Path
from typing import Iterator, Dict, Any
from dataclasses import dataclass

@dataclass
class FileInfo:
    filepath: str
    size: int
    modified_time: float
    file_hash: str
    extension: str

class FileScanner:
    """Recursively scan directories for conversation files"""
    
    SUPPORTED_EXTENSIONS = {'.json', '.csv', '.txt', '.xml', '.tsv'}
    
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self.file_cache = {}
    
    def scan_directory(self, path: str) -> Iterator[FileInfo]:
        """Scan directory recursively for supported files"""
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        
        for file_path in path_obj.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                try:
                    file_info = self._create_file_info(file_path)
                    if self._should_process_file(file_info):
                        yield file_info
                except (OSError, PermissionError) as e:
                    print(f"Warning: Cannot access {file_path}: {e}")
                    continue
    
    def _create_file_info(self, file_path: Path) -> FileInfo:
        """Create FileInfo object for a file"""
        stat = file_path.stat()
        file_hash = self.get_file_hash(str(file_path)) if self.cache_enabled else ""
        
        return FileInfo(
            filepath=str(file_path),
            size=stat.st_size,
            modified_time=stat.st_mtime,
            file_hash=file_hash,
            extension=file_path.suffix.lower()
        )
    
    def get_file_hash(self, filepath: str) -> str:
        """Generate hash for file (for incremental processing)"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _should_process_file(self, file_info: FileInfo) -> bool:
        """Check if file should be processed (incremental processing)"""
        if not self.cache_enabled:
            return True
        
        cached_info = self.file_cache.get(file_info.filepath)
        if cached_info is None:
            self.file_cache[file_info.filepath] = file_info
            return True
        
        # Check if file changed
        if (cached_info.file_hash != file_info.file_hash or 
            cached_info.modified_time != file_info.modified_time):
            self.file_cache[file_info.filepath] = file_info
            return True
        
        return False