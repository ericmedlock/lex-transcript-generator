#!/usr/bin/env python3
"""
AWS Transcribe JSON Translator - Convert AWS Transcribe output to conversation format
"""

import json
from pathlib import Path
from typing import Dict, List, Any

class AWSTranscribeTranslator:
    """Translates AWS Transcribe JSON files to conversation format"""
    
    def __init__(self):
        self.name = "AWS Transcribe"
        self.supported_extensions = [".json"]
    
    def can_translate(self, file_path: Path) -> bool:
        """Check if this translator can handle the file"""
        if file_path.suffix.lower() not in self.supported_extensions:
            return False
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Check for AWS Transcribe structure
                return (
                    "results" in data and 
                    "transcripts" in data.get("results", {}) and
                    "speaker_labels" in data.get("results", {})
                )
        except:
            return False
    
    def translate(self, file_path: Path) -> Dict[str, Any]:
        """Translate AWS Transcribe JSON to conversation format"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract basic info
        job_name = data.get("jobName", "")
        status = data.get("status", "")
        
        # Get transcript and speaker info
        results = data.get("results", {})
        audio_segments = results.get("audio_segments", [])
        
        conversation_turns = []
        
        if audio_segments:
            # Use audio segments (cleaner format)
            for segment in audio_segments:
                speaker = segment.get("speaker_label", "unknown")
                text = segment.get("transcript", "")
                start_time = segment.get("start_time", "0")
                end_time = segment.get("end_time", "0")
                
                if text.strip():
                    conversation_turns.append({
                        "speaker": speaker,
                        "text": text.strip(),
                        "start_time": float(start_time),
                        "end_time": float(end_time)
                    })
        
        # Convert to conversation format
        conversation_text = self._format_conversation(conversation_turns)
        
        return {
            "source_type": "aws_transcribe",
            "job_name": job_name,
            "status": status,
            "conversation_text": conversation_text,
            "speaker_count": len(set(turn["speaker"] for turn in conversation_turns)),
            "turn_count": len(conversation_turns),
            "duration": max([turn["end_time"] for turn in conversation_turns]) if conversation_turns else 0,
            "metadata": {
                "file_path": str(file_path),
                "original_format": "aws_transcribe_json"
            }
        }
    
    def _format_conversation(self, turns: List[Dict]) -> str:
        """Format conversation turns into readable text"""
        if not turns:
            return ""
        
        # Map speaker labels to readable names
        speaker_map = {}
        unique_speakers = list(set(turn["speaker"] for turn in turns))
        
        for i, speaker in enumerate(sorted(unique_speakers)):
            if speaker.startswith("spk_"):
                speaker_num = speaker.replace("spk_", "")
                if speaker_num == "0":
                    speaker_map[speaker] = "Agent"
                else:
                    speaker_map[speaker] = "Customer"
            else:
                speaker_map[speaker] = f"Speaker_{i+1}"
        
        # Format conversation
        formatted_lines = []
        for turn in turns:
            speaker_name = speaker_map.get(turn["speaker"], turn["speaker"])
            formatted_lines.append(f"{speaker_name}: {turn['text']}")
        
        return "\n".join(formatted_lines)

def get_translator():
    """Factory function to get translator instance"""
    return AWSTranscribeTranslator()