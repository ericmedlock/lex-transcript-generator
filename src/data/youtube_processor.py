"""YouTube and video processing with audio extraction"""

import yt_dlp
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from .audio_processor import AudioProcessor


class YouTubeProcessor:
    def __init__(self):
        self.audio_processor = AudioProcessor()
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'temp_audio/%(title)s.%(ext)s',
            'extractaudio': True,
            'audioformat': 'wav'
        }

    async def process_url(self, url: str) -> Dict[str, Any]:
        """Process YouTube URL and extract audio"""
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_file = ydl.prepare_filename(info).replace('.webm', '.wav')
            
            # Process extracted audio
            audio_data = await self.audio_processor.process_file(audio_file)
            
            return {
                'title': info.get('title'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'audio_data': audio_data,
                'url': url
            }

    async def process_playlist(self, playlist_url: str) -> List[Dict[str, Any]]:
        """Process entire YouTube playlist"""
        with yt_dlp.YoutubeDL({'extract_flat': True}) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            
        results = []
        for entry in playlist_info['entries']:
            if entry:
                video_url = f"https://youtube.com/watch?v={entry['id']}"
                result = await self.process_url(video_url)
                results.append(result)
                
        return results