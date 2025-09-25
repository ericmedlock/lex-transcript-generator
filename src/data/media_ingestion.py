"""Media ingestion pipeline for various audio/video formats"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List
from .audio_processor import AudioProcessor
from .youtube_processor import YouTubeProcessor


class MediaIngestionPipeline:
    def __init__(self):
        self.audio_processor = AudioProcessor()
        self.youtube_processor = YouTubeProcessor()
        
    async def process_media(self, source: str, source_type: str) -> Dict[str, Any]:
        """Process media from various sources"""
        
        if source_type == 'youtube':
            return await self.youtube_processor.process_url(source)
        
        elif source_type in ['mp4', 'mp3', 'audio', 'upload']:
            return await self.audio_processor.process_file(source)
        
        elif source_type == 'youtube_playlist':
            return await self.youtube_processor.process_playlist(source)
        
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
    
    async def batch_process_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Process multiple files concurrently"""
        tasks = []
        for file_path in file_paths:
            # Determine type from extension
            ext = Path(file_path).suffix.lower()
            if ext in ['.mp4', '.avi', '.mov']:
                source_type = 'mp4'
            elif ext in ['.mp3', '.wav', '.m4a']:
                source_type = 'mp3'
            else:
                source_type = 'audio'
                
            task = self.process_media(file_path, source_type)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)