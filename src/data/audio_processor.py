"""Audio processing for MP4, MP3, and other audio formats"""

import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import librosa
import soundfile as sf
from moviepy.editor import VideoFileClip


class AudioProcessor:
    def __init__(self):
        self.supported_formats = {
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm'],
            'audio': ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac']
        }

    async def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process audio/video file and extract audio"""
        path = Path(file_path)
        
        if path.suffix.lower() in self.supported_formats['video']:
            return await self._extract_audio_from_video(file_path)
        elif path.suffix.lower() in self.supported_formats['audio']:
            return await self._process_audio_file(file_path)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")

    async def _extract_audio_from_video(self, video_path: str) -> Dict[str, Any]:
        """Extract audio from video file"""
        video_path = Path(video_path)
        audio_path = video_path.with_suffix('.wav')
        
        # Use moviepy for video processing
        with VideoFileClip(str(video_path)) as video:
            audio = video.audio
            audio.write_audiofile(str(audio_path), verbose=False, logger=None)
        
        return await self._process_audio_file(str(audio_path))

    async def _process_audio_file(self, audio_path: str) -> Dict[str, Any]:
        """Process audio file and return metadata"""
        # Load and normalize audio
        audio, sr = librosa.load(audio_path, sr=16000)
        
        # Get audio metadata
        duration = len(audio) / sr
        
        # Save normalized version
        normalized_path = Path(audio_path).with_name(f"normalized_{Path(audio_path).name}")
        sf.write(str(normalized_path), audio, sr)
        
        return {
            'original_path': audio_path,
            'processed_path': str(normalized_path),
            'duration': duration,
            'sample_rate': sr,
            'channels': 1,
            'format': 'wav'
        }

    async def convert_to_wav(self, input_path: str, output_path: str = None) -> str:
        """Convert any audio format to WAV"""
        if not output_path:
            output_path = Path(input_path).with_suffix('.wav')
        
        # Use ffmpeg for conversion
        cmd = [
            'ffmpeg', '-i', input_path,
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',      # Mono
            '-y',            # Overwrite output
            str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        return str(output_path)